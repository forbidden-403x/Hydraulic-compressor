import engine
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

ALGORITHMS = {
    "zip": ".hy1",
    "gzip": ".hy2",
    "lzma": ".hy3",
}


# ============================================================
# UI HELPERS
# ============================================================

def line():
    print("=" * 60)


def progress(p):
    print(
        f"\rProgress: {p.percent:6.2f}%",
        end="",
        flush=True
    )


def ask(prompt, default=""):
    value = input(prompt).strip()
    return value if value else default


# ============================================================
# MAIN
# ============================================================

def main():

    line()
    print("              HYDRAULIC ENGINE TESTER")
    line()

    # --------------------------------------------------------
    # FILE
    # --------------------------------------------------------

    file = ask("\nFile to test: ")

    if not file:
        print("No file specified.")
        return

    source = Path(file).expanduser().resolve()

    if not source.is_file():
        print(f"\nERROR: File not found:\n{source}")
        return

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    print("\n[1] ANALYSIS")
    line()

    try:
        info = engine.analyse(source)

        print(f"Name:              {info.name}")
        print(f"Size:              {engine.human_size(info.size)}")
        print(f"Extension:         {info.extension or '(none)'}")
        print(f"Entropy:           {info.entropy:.4f} / 8")
        print(f"Entropy:           {info.entropy_percent:.2f}%")
        print(f"Compressibility:   {info.compressibility}")
        print(f"Already compressed:{' YES' if info.likely_compressed else ' NO'}")

    except Exception as exc:
        print("\nANALYSIS FAILED")
        print(type(exc).__name__, exc)
        return

    # --------------------------------------------------------
    # RECOMMENDATION
    # --------------------------------------------------------

    print("\n[2] RECOMMENDATION")
    line()

    try:
        recommendation = engine.reccomend_algo(info)

        algorithm = recommendation["algorithm"]

        print(
            f"Algorithm:         "
            f"{algorithm.upper() if algorithm else 'NONE'}"
        )
        print(f"Pressure:          {recommendation['pressure']}")
        print(f"Reason:            {recommendation['reason']}")
        print(
            f"Compress:          "
            f"{'YES' if recommendation['compress'] else 'NO'}"
        )

    except Exception as exc:
        print("\nRECOMMENDATION FAILED")
        print(type(exc).__name__, exc)
        return

    # --------------------------------------------------------
    # COMPRESSION SETTINGS
    # --------------------------------------------------------

    print("\n[3] COMPRESSION")
    line()

    algorithm = ask(
        "Algorithm [zip/gzip/lzma] (default: zip): ",
        "zip"
    ).lower()

    if algorithm not in ALGORITHMS:
        print(f"Unknown algorithm: {algorithm}")
        print("Available:", ", ".join(ALGORITHMS))
        return

    pressure = ask(
        "Pressure [low/medium/high/maximum] (default: medium): ",
        "medium"
    ).lower()

    valid_pressure = {
        "low",
        "medium",
        "high",
        "maximum",
    }

    if pressure not in valid_pressure:
        print(f"Unknown pressure: {pressure}")
        return

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    extension = ALGORITHMS[algorithm]

    output = source.with_name(
        source.stem + "_hydraulic" + extension
    )

    print()
    print(f"Algorithm:         {algorithm.upper()}")
    print(f"Pressure:          {pressure.upper()}")
    print(f"Output:            {output}")
    print()

    print("Compressing...")

    try:

        result = engine.compress(
            source,
            output,
            algorithm=algorithm,
            pressure=pressure,
            progress_callback=progress,
        )

        print("\n")
        print("COMPRESSION COMPLETE")
        line()

        print(
            f"Original:          "
            f"{engine.human_size(result.original_size)}"
        )

        print(
            f"Compressed:        "
            f"{engine.human_size(result.compressed_size)}"
        )

        print(
            f"Saved:             "
            f"{engine.human_size(result.saved_bytes)}"
        )

        print(
            f"Reduction:         "
            f"{result.reduction_percent:.2f}%"
        )

        print(
            f"Ratio:             "
            f"{result.compression_ratio:.3f}:1"
        )

        print(
            f"Time:              "
            f"{result.elapsed_seconds:.3f}s"
        )

        print(
            f"Speed:             "
            f"{result.speed_mbps:.2f} MB/s"
        )

        print(
            f"Verified:          "
            f"{'YES ✓' if result.verified else 'NO ✗'}"
        )

        print(
            f"Output SHA-256:    "
            f"{result.compressed_sha256}"
        )

    except Exception as exc:

        print("\n")
        print("COMPRESSION FAILED")
        line()
        print(type(exc).__name__, exc)
        return

    # --------------------------------------------------------
    # DECOMPRESSION TEST
    # --------------------------------------------------------

    print("\n[4] DECOMPRESSION TEST")
    line()

    answer = ask(
        "Test decompression? [Y/n]: ",
        "y"
    ).lower()

    if answer == "y":

        extract_dir = source.parent / "hydraulic_test_output"

        # Avoid accidentally overwriting an existing folder.
        if extract_dir.exists():
            number = 2

            while True:
                candidate = source.parent / (
                    f"hydraulic_test_output_{number}"
                )

                if not candidate.exists():
                    extract_dir = candidate
                    break

                number += 1

        print(f"Output directory: {extract_dir}")
        print("Decompressing...")

        try:

            engine.decompress(
                output,
                extract_dir,
                algorithm=extension,
                progress_callback=progress,
            )

            print("\n")
            print("DECOMPRESSION COMPLETE ✓")
            print(f"Extracted to: {extract_dir}")

        except Exception as exc:

            print("\n")
            print("DECOMPRESSION FAILED")
            print(type(exc).__name__, exc)

    # --------------------------------------------------------
    # BENCHMARK
    # --------------------------------------------------------

    print("\n[5] BENCHMARK")
    line()

    answer = ask(
        "Run benchmark? [Y/n]: ",
        "y"
    ).lower()

    if answer == "y":

        print("\nTesting all algorithms and pressure levels...\n")

        try:

            results = engine.benchmark(
                source,
                algorithms=[
                    "zip",
                    "gzip",
                    "lzma",
                ],
                levels=[
                    1,
                    5,
                    9,
                ],
            )

            print(
                f"{'ENGINE':<10}"
                f"{'LEVEL':<8}"
                f"{'SIZE':<14}"
                f"{'REDUCTION':<13}"
                f"{'TIME':<10}"
                f"{'SPEED':<12}"
            )

            print("-" * 67)

            valid_results = []

            for r in results:

                if r.error:

                    print(
                        f"{r.algorithm.upper():<10}"
                        f"{r.level:<8}"
                        f"ERROR: {r.error}"
                    )

                    continue

                valid_results.append(r)

                print(
                    f"{r.algorithm.upper():<10}"
                    f"{r.level:<8}"
                    f"{engine.human_size(r.compressed_size):<14}"
                    f"{r.reduction_percent:>7.2f}%     "
                    f"{r.elapsed_seconds:>7.3f}s  "
                    f"{r.speed_mbps:>7.2f} MB/s"
                )

            # ------------------------------------------------
            # BEST RESULT
            # ------------------------------------------------

            if valid_results:

                smallest = min(
                    valid_results,
                    key=lambda r: r.compressed_size
                )

                fastest = min(
                    valid_results,
                    key=lambda r: r.elapsed_seconds
                )

                print()
                line()
                print("BEST RESULTS")
                line()

                print(
                    f"Smallest:  "
                    f"{smallest.algorithm.upper()} "
                    f"level {smallest.level} → "
                    f"{engine.human_size(smallest.compressed_size)}"
                )

                print(
                    f"Fastest:   "
                    f"{fastest.algorithm.upper()} "
                    f"level {fastest.level} → "
                    f"{fastest.elapsed_seconds:.3f}s"
                )

        except Exception as exc:

            print("\nBENCHMARK FAILED")
            print(type(exc).__name__, exc)

    # --------------------------------------------------------
    # DONE
    # --------------------------------------------------------

    print()
    line()
    print("             HYDRAULIC TEST COMPLETE")
    line()


if __name__ == "__main__":
    main()