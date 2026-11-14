# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary

"""Exercise documented capture and incremental reads through the public native API."""

import csv
import json

import ovrtx
import pytest


@pytest.mark.parametrize("save_to_file", [False, True])
def test_profiling_capture_and_updates(stage, tmp_path, save_to_file):
    """Check restart isolation, retained progress, owned copies, JSON, and flushed CSV data."""
    import ovrtx

    output_path = str(tmp_path) if save_to_file else None

    data = ovrtx.ovrtx_performance_data_update_t()
    try:
        # Each session uses different values so stale retained data fails the test.
        for session in range(2):
            if save_to_file:
                # [snippet:doc-profiling-file-python]
                from pathlib import Path
                import ovrtx

                # Choose a directory before starting; start_profiling does not create it.
                capture_dir = Path(output_path)
                capture_dir.mkdir(parents=True, exist_ok=True)
                ovrtx.start_profiling(output_path=str(capture_dir), file_name="profiling")
                # [/snippet:doc-profiling-file-python]
            else:
                import ovrtx

                ovrtx.start_profiling()  # Live capture without files.
            try:
                fps_uid = ovrtx.OVRTX_PERFORMANCE_PREDEFINED_METRIC_UID_FPS
                with pytest.raises(RuntimeError, match="already active"):
                    ovrtx.start_profiling()

                first_value = 101.0 + session * 10
                ovrtx.add_performance_metric_value(fps_uid, first_value)
                # [snippet:doc-profiling-read-python]
                import ovrtx

                # data is zero-initialized once and retained between reads and restarts.
                collection_time, metrics = ovrtx.get_performance_data_update(data)
                for metric in metrics:
                    for sample in metric["values"]:
                        print(
                            metric["name"], sample["timestamp_ns"],
                            sample["value"], metric["units"],
                        )
                # [/snippet:doc-profiling-read-python]
                first = next(metric for metric in metrics if metric["uid"] == fps_uid)
                assert [sample["value"] for sample in first["values"]] == [first_value]
                assert all(sample["timestamp_ns"] > 0 for metric in metrics for sample in metric["values"])

                ovrtx.add_performance_metric_value(fps_uid, first_value + 1)
                # [snippet:doc-profiling-json-python]
                import json
                import ovrtx

                # JSON and structured reads advance the same retained batch.
                collection_time, text = ovrtx.get_performance_data_update_as_json(data)
                update = json.loads(text)
                # [/snippet:doc-profiling-json-python]
                assert update["collection_time_ns"] == collection_time
                second = next(metric for metric in update["metrics"] if metric["uid"] == fps_uid)
                assert [sample["value"] for sample in second["values"]] == [first_value + 1]
                assert [sample["value"] for sample in first["values"]] == [first_value]
                _, followup = ovrtx.get_performance_data_update(data)
                assert not next(metric for metric in followup if metric["uid"] == fps_uid)["values"]

                ovrtx.add_performance_metric_value(fps_uid, first_value + 2)
                # [snippet:doc-profiling-replay-python]
                import ovrtx

                # A separate batch rereads retained history without advancing data.
                history_data = ovrtx.ovrtx_performance_data_update_t()
                try:
                    history_time, history = ovrtx.get_performance_data_update(history_data)
                finally:
                    ovrtx.release_performance_data_update(history_data)
                next_time, newer = ovrtx.get_performance_data_update(data)
                # [/snippet:doc-profiling-replay-python]
                fps_history = next(metric for metric in history if metric["uid"] == fps_uid)
                assert [sample["value"] for sample in fps_history["values"]] == [first_value, first_value + 1, first_value + 2]
                assert [sample["value"] for sample in next(
                    metric for metric in newer if metric["uid"] == fps_uid
                )["values"]] == [first_value + 2]
                assert next_time >= history_time >= collection_time
            finally:
                # Run in a finally block while the renderer is still alive.
                ovrtx.stop_profiling()
            ovrtx.stop_profiling()
    finally:
        # [snippet:doc-profiling-stop-python]
        # Both cleanup calls run while the renderer is still alive.
        try:
            ovrtx.release_performance_data_update(data)
        finally:
            ovrtx.stop_profiling()
        # [/snippet:doc-profiling-stop-python]

    if save_to_file:
        for suffix in ("info", "data", "summary"):
            paths = list(tmp_path.glob(f"*.rpm_{suffix}.csv"))
            assert len(paths) == 2, "Restart must preserve the previous recording"
            for path in paths:
                with path.open(encoding="utf-8-sig", newline="") as stream:
                    uids = {int(row[0]) for row in csv.reader(stream) if row and row[0].isdigit()}
                assert fps_uid in uids, f"Missing captured FPS in {path}"
    else:
        assert not list(tmp_path.iterdir())


def test_profiling_render_loop(renderer, stage):
    """Run the complete polling example against rendered work, checking retained progress and RTX samples."""
    from pathlib import Path
    import ovstage

    scene = Path(__file__).resolve().parent / "../data/ovrtx-test-base.usda"
    ovstage.population.open_usd(stage, str(scene), ordinal=1)
    stage.advance_write_floor(1, ovstage.Scope.ALL).wait()
    ordinal = 1

    # [snippet:doc-profiling-render-loop-python]
    import time
    import ovrtx

    # renderer has an attached stage with /Render/Camera committed at ordinal.
    data = ovrtx.ovrtx_performance_data_update_t()
    next_read = time.monotonic()
    updates = []
    ovrtx.start_profiling()
    try:
        for frame in range(60):
            renderer.step(
                render_products={"/Render/Camera"},
                delta_time=1 / 60,
                ordinal=ordinal,
            )

            # Render every frame, but copy profiling data at most twice per second.
            # Also read after the last frame to collect the latest available samples.
            now = time.monotonic()
            if now >= next_read or frame == 59:
                collection_time, metrics = ovrtx.get_performance_data_update(data)
                updates.append((collection_time, metrics))  # Python owns these copies.
                next_read = now + 0.5
    finally:
        try:
            ovrtx.release_performance_data_update(data)
        finally:
            ovrtx.stop_profiling()

    # Python-owned copies survive batch reuse and release.
    for collection_time, metrics in updates:
        for metric in metrics:
            for sample in metric["values"]:
                print(
                    metric["name"], sample["timestamp_ns"],
                    sample["value"], metric["units"],
                )
    # [/snippet:doc-profiling-render-loop-python]

    assert len(updates) >= 2
    previous = 0
    rtx_samples = []
    for collection_time, metrics in updates:
        assert collection_time >= previous
        rtx_samples.extend(sample for metric in metrics if metric["name"].startswith("RTX Rendering")
                           for sample in metric["values"])
        previous = collection_time
    assert rtx_samples, "The example must collect actual RTX rendering measurements"
    assert all(sample["value"] >= 0 for sample in rtx_samples)
