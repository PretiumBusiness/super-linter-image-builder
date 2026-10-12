#!/usr/bin/env python3
"""Monte Carlo model of cold `docker pull` time, calibrated to an observed slim pull.

What it does
    1. Draws component sizes (from sim/components.json) and environment parameters
        (bandwidth, decompression and disk speed, per-file cost) from priors.
    2. Computes the cold pull time of each image variant: layers download with a
        small number of parallel streams, then are extracted strictly in order.
    3. Keeps only the draws where the *slim* pull time falls in the range you
        actually observe (default 60-90 s), then reports the lean variants for
        those draws. This is rejection-sampling calibration (ABC): the unknown
        environment parameters get pinned to your real number.

Important: component sizes in components.json are estimates. Treat the output
as a prediction with error bars, not a measurement. Replace the estimates with
real layer data (sim/profile-image.sh, then --measured) as soon as you have it.

Usage
    python3 sim/pull_model.py [--draws 60000] [--observed 60 90] [--seed 1]
    python3 sim/pull_model.py --measured slim=layers-slim.json lean=layers-lean.json
"""

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

STREAMS = 3  # docker default max-concurrent-downloads
STARTUP_S = 1.0  # manifest, auth, bookkeeping
PER_LAYER_S = 0.05  # fixed cost per layer


def download_done_times(comp_mb, bandwidth, per_conn):
    """Layers start in order, STREAMS at a time; each stream gets
    min(per_conn, bandwidth / active)."""
    n = len(comp_mb)
    remaining = list(comp_mb)
    done = [0.0] * n
    active, nxt, t, finished = [], 0, 0.0, 0
    while finished < n:
        while len(active) < STREAMS and nxt < n:
            active.append(nxt)
            nxt += 1
        rate = min(per_conn, bandwidth / len(active))
        dt = min(remaining[i] for i in active) / rate
        t += dt
        for i in active:
            remaining[i] -= rate * dt
        for i in [i for i in active if remaining[i] <= 1e-9]:
            done[i] = t
            active.remove(i)
            finished += 1
    return done


def pull_time(layers, env, zstd=False):
    """layers: list of dicts with comp_mb, unc_mb, files. Returns (total_s, extract_s)."""
    comp = [l["comp_mb"] * (env["zstd_ratio"] if zstd else 1.0) for l in layers]
    done = download_done_times(comp, env["bandwidth"], env["per_conn"])
    decomp = env["decomp_gz"] * (env["zstd_speedup"] if zstd else 1.0)
    end = 0.0
    ext_total = 0.0
    for l, d in zip(layers, done):
        ext = (
            l["unc_mb"] / decomp
            + l["unc_mb"] / env["disk_write"]
            + l["files"] * env["per_file_us"] * 1e-6
            + PER_LAYER_S
        )
        ext_total += ext
        end = max(end, d) + ext
    return end + STARTUP_S, ext_total


# Prior ranges for the environment. Override with --bandwidth / --per-file to
# test download-bound or unpack-bound worlds.
RANGES = {
    "bandwidth": (30, 250),  # MB/s aggregate from registry
    "per_conn": (10, 80),  # MB/s per download stream
    "decomp_gz": (70, 200),  # MB/s gzip output
    "disk_write": (250, 800),  # MB/s sequential write
    "per_file_us": (10, 80),  # microseconds per extracted file
}


def draw_env(rng):
    return {
        "bandwidth": rng.uniform(*RANGES["bandwidth"]),
        "per_conn": rng.uniform(*RANGES["per_conn"]),
        "decomp_gz": rng.uniform(*RANGES["decomp_gz"]),
        "disk_write": rng.uniform(*RANGES["disk_write"]),
        "per_file_us": rng.uniform(*RANGES["per_file_us"]),
        "zstd_speedup": rng.uniform(2.0, 4.0),  # zstd vs gzip decompression speed
        "zstd_ratio": rng.uniform(0.82, 0.95),  # zstd size relative to gzip
    }


def draw_components(components, rng):
    drawn = {}
    for c in components:
        unc = rng.uniform(*c["unc"])
        drawn[c["id"]] = {
            "id": c["id"],
            "kind": c["kind"],
            "unc_mb": unc,
            "files": rng.uniform(*c["files"]),
            "comp_mb": unc * c["ratio"] * rng.uniform(0.85, 1.15),
        }
    return drawn


def build_layers(variant, components, drawn):
    """Slim bundles all venvs into one layer (single COPY); the overlay copies
    each tool separately."""
    members = [drawn[c["id"]] for c in components if variant in c["in"]]
    if variant != "slim":
        return members
    venvs = [m for m in members if m["kind"] == "venv"]
    rest = [m for m in members if m["kind"] != "venv"]
    merged = {k: sum(v[k] for v in venvs) for k in ("unc_mb", "files", "comp_mb")}
    merged.update(id="venvs", kind="venv")
    # place the merged venv layer where upstream does: after the binaries
    return rest + [merged]


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))]


def run_simulation(args):
    spec = json.loads(Path(args.components).read_text())
    components = spec["components"]
    variant_names = list(spec["variants"])
    rng = random.Random(args.seed)
    lo, hi = args.observed
    acc = {v: [] for v in variant_names}
    sizes = {v: [] for v in variant_names}
    ext_share = {v: [] for v in variant_names}
    accepted = 0
    for _ in range(args.draws):
        env = draw_env(rng)
        drawn = draw_components(components, rng)
        times = {}
        for v in variant_names:
            layers = build_layers(v, components, drawn)
            times[v] = (pull_time(layers, env, zstd=v.endswith("_zstd")), layers)
        slim_t = times["slim"][0][0]
        if not lo <= slim_t <= hi:
            continue
        accepted += 1
        for v in variant_names:
            (t, ext), layers = times[v]
            acc[v].append(t)
            ext_share[v].append(ext / t)
            sizes[v].append(
                (
                    sum(l["comp_mb"] for l in layers) / 1024,
                    sum(l["unc_mb"] for l in layers) / 1024,
                    sum(l["files"] for l in layers),
                )
            )
    if accepted < 50:
        sys.exit(f"only {accepted} draws matched slim in {lo}-{hi}s; widen --observed or --draws")
    return spec, variant_names, acc, sizes, ext_share, accepted


def run_measured(args):
    """Use real layer lists; only the environment is uncertain."""
    layer_sets = {}
    for item in args.measured:
        name, path = item.split("=", 1)
        layer_sets[name] = json.loads(Path(path).read_text())
    if "slim" not in layer_sets:
        sys.exit("--measured needs a slim=... entry for calibration")
    rng = random.Random(args.seed)
    lo, hi = args.observed
    acc = {v: [] for v in layer_sets}
    accepted = 0
    for _ in range(args.draws):
        env = draw_env(rng)
        t = {v: pull_time(l, env, zstd=v.endswith("_zstd"))[0] for v, l in layer_sets.items()}
        if lo <= t["slim"] <= hi:
            accepted += 1
            for v in layer_sets:
                acc[v].append(t[v])
    if accepted < 50:
        sys.exit(f"only {accepted} draws matched; widen --observed")
    return acc, accepted


def table(spec, names, acc, sizes, ext_share, accepted, args):
    lo, hi = args.observed
    out = [
        f"Draws kept: {accepted} of {args.draws} (slim pull simulated in {lo}-{hi} s)",
        "",
        "| Variant | Pull median | p10-p90 | vs slim | Compressed GB | Unpacked GB | Files (k) | Unpack share |",
        "|---|---|---|---|---|---|---|---|",
    ]
    slim_med = statistics.median(acc["slim"])
    for v in names:
        t = acc[v]
        med = statistics.median(t)
        comp = statistics.median(s[0] for s in sizes[v])
        unc = statistics.median(s[1] for s in sizes[v])
        files = statistics.median(s[2] for s in sizes[v]) / 1000
        out.append(
            f"| {v} | {med:.0f} s | {pct(t, 0.1):.0f}-{pct(t, 0.9):.0f} s | "
            f"{slim_med / med:.1f}x | {comp:.2f} | {unc:.2f} | {files:.0f} | "
            f"{statistics.median(ext_share[v]) * 100:.0f}% |"
        )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--components", default=str(Path(__file__).with_name("components.json")))
    ap.add_argument("--draws", type=int, default=60000)
    ap.add_argument(
        "--observed",
        type=float,
        nargs=2,
        default=[60, 90],
        metavar=("LO", "HI"),
        help="observed slim cold pull time range in seconds",
    )
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument(
        "--measured",
        nargs="+",
        metavar="NAME=FILE",
        help="real layer lists (from profile-image.sh) instead of estimated components",
    )
    ap.add_argument("--json", metavar="FILE", help="also write summary JSON")
    ap.add_argument(
        "--bandwidth", type=float, nargs=2, metavar=("LO", "HI"), help="aggregate registry bandwidth prior, MB/s"
    )
    ap.add_argument(
        "--per-conn", type=float, nargs=2, metavar=("LO", "HI"), help="per-download-stream bandwidth prior, MB/s"
    )
    ap.add_argument(
        "--per-file", type=float, nargs=2, metavar=("LO", "HI"), help="per-file extraction cost prior, microseconds"
    )
    args = ap.parse_args()
    if args.bandwidth:
        RANGES["bandwidth"] = tuple(args.bandwidth)
    if args.per_conn:
        RANGES["per_conn"] = tuple(args.per_conn)
    if args.per_file:
        RANGES["per_file_us"] = tuple(args.per_file)

    if args.measured:
        acc, accepted = run_measured(args)
        slim_med = statistics.median(acc["slim"])
        print(f"Draws kept: {accepted} of {args.draws}\n")
        print("| Variant | Pull median | p10-p90 | vs slim |\n|---|---|---|---|")
        for v, t in acc.items():
            m = statistics.median(t)
            print(f"| {v} | {m:.0f} s | {pct(t, 0.1):.0f}-{pct(t, 0.9):.0f} s | {slim_med / m:.1f}x |")
        return

    spec, names, acc, sizes, ext_share, accepted = run_simulation(args)
    print(table(spec, names, acc, sizes, ext_share, accepted, args))
    if args.json:
        summary = {
            v: {
                "median_s": statistics.median(acc[v]),
                "p10_s": pct(acc[v], 0.1),
                "p90_s": pct(acc[v], 0.9),
                "compressed_gb": statistics.median(s[0] for s in sizes[v]),
                "unpacked_gb": statistics.median(s[1] for s in sizes[v]),
            }
            for v in names
        }
        Path(args.json).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
