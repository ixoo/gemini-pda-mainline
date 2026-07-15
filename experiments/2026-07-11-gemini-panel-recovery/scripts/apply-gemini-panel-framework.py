#!/usr/bin/env python3
"""Apply the generated Gemini descriptor to a disposable kernel clone.

This is an authoring helper, not a build step.  It is kept beside the table
generator so patch regeneration can be repeated against a pinned source tree.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"expected one replacement, found {source.count(old)}")
    return source.replace(old, new)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clone", type=Path, required=True)
    parser.add_argument("--vendor-git", type=Path, required=True)
    args = parser.parse_args()

    source_path = args.clone / "drivers/gpu/drm/panel/panel-novatek-nt36672e.c"
    source = source_path.read_text()
    generator = Path(__file__).with_name("emit-gemini-panel-init.py")
    generated = subprocess.check_output(
        ["python3", str(generator), "--vendor-git", str(args.vendor_git)],
        text=True,
    ).rstrip()

    source = replace_once(
        source,
        """struct panel_desc {
\tconst struct drm_display_mode *display_mode;
\tu32 width_mm;
\tu32 height_mm;
\tunsigned long mode_flags;
\tenum mipi_dsi_pixel_format format;
\tunsigned int lanes;
\tconst char *panel_name;
\tvoid (*init_sequence)(struct mipi_dsi_multi_context *ctx);
};""",
        """struct panel_desc {
\tconst char * const *supply_names;
\tunsigned int num_supplies;
\tconst struct drm_display_mode *display_mode;
\tu32 width_mm;
\tu32 height_mm;
\tunsigned long mode_flags;
\tenum mipi_dsi_pixel_format format;
\tunsigned int lanes;
\tconst char *panel_name;
\tvoid (*init_sequence)(struct mipi_dsi_multi_context *ctx);
\tunsigned int power_on_delay_ms;
\tunsigned int reset_high_delay_ms;
\tunsigned int reset_low_delay_ms;
\tunsigned int reset_final_high_delay_ms;
\tunsigned int display_off_delay_ms;
\tunsigned int sleep_in_delay_ms;
\tunsigned int exit_sleep_delay_ms;
\tunsigned int display_on_delay_ms;
};""",
    )

    old = """static int nt36672e_power_on(struct nt36672e_panel *ctx)
{
\tstruct mipi_dsi_device *dsi = ctx->dsi;
\tint ret;

\tret = regulator_bulk_enable(ARRAY_SIZE(ctx->supplies), ctx->supplies);
\tif (ret < 0) {
\t\tdev_err(&dsi->dev, "regulator bulk enable failed: %d\\n", ret);
\t\treturn ret;
\t}

\t/*
\t * Reset sequence of nt36672e panel requires the panel to be out of reset
\t * for 10ms, followed by being held in reset for 10ms and then out again.
\t */
\tgpiod_set_value(ctx->reset_gpio, 1);
\tusleep_range(10000, 20000);
\tgpiod_set_value(ctx->reset_gpio, 0);
\tusleep_range(10000, 20000);
\tgpiod_set_value(ctx->reset_gpio, 1);
\tusleep_range(10000, 20000);

\treturn 0;
}"""
    new = """static void nt36672e_gemini_write_cmd(struct mipi_dsi_multi_context *ctx,
\t\t\t\t      const u8 *data, unsigned int len)
{
\tmipi_dsi_dcs_write_buffer_multi(ctx, data, len);
}

""" + generated + """

static void nt36672e_delay_ms(unsigned int delay_ms)
{
\tif (delay_ms)
\t\tusleep_range(delay_ms * 1000, (delay_ms + 10) * 1000);
}

static int nt36672e_power_on(struct nt36672e_panel *ctx)
{
\tstruct mipi_dsi_device *dsi = ctx->dsi;
\tconst struct panel_desc *desc = ctx->desc;
\tint ret;

\t/* Keep reset asserted while the descriptor-selected rails come up. */
\tgpiod_set_value(ctx->reset_gpio, 0);

\tret = regulator_bulk_enable(desc->num_supplies, ctx->supplies);
\tif (ret < 0) {
\t\tdev_err(&dsi->dev, "regulator bulk enable failed: %d\\n", ret);
\t\treturn ret;
\t}

\tmsleep(desc->power_on_delay_ms);

\t/*
\t * The existing NT36672E sequence is 10ms high, 10ms low, then high.
\t * Gemini uses the same pattern after its 20ms bias-settle delay, with
\t * a 20ms final high interval.
\t */
\tgpiod_set_value(ctx->reset_gpio, 1);
\tnt36672e_delay_ms(desc->reset_high_delay_ms);
\tgpiod_set_value(ctx->reset_gpio, 0);
\tnt36672e_delay_ms(desc->reset_low_delay_ms);
\tgpiod_set_value(ctx->reset_gpio, 1);
\tnt36672e_delay_ms(desc->reset_final_high_delay_ms);

\treturn 0;
}"""
    new = new.replace(
        "mipi_dsi_dcs_write_buffer_multi(ctx, data, len);",
        "if (data[0] >= 0xb0)\\n"
        "        mipi_dsi_generic_write_multi(ctx, data, len);\\n"
        "else\\n"
        "        mipi_dsi_dcs_write_buffer_multi(ctx, data, len);",
        1,
    )
    source = replace_once(source, old, new)
    source = replace_once(
        source,
        "\tret = regulator_bulk_disable(ARRAY_SIZE(ctx->supplies), ctx->supplies);",
        "\tret = regulator_bulk_disable(ctx->desc->num_supplies, ctx->supplies);",
    )
    source = replace_once(
        source,
        """\tmipi_dsi_dcs_exit_sleep_mode_multi(&ctx);
\tmipi_dsi_msleep(&ctx, 120);

\tmipi_dsi_dcs_set_display_on_multi(&ctx);

\tmipi_dsi_msleep(&ctx, 100);""",
        """\tmipi_dsi_dcs_exit_sleep_mode_multi(&ctx);
\tmipi_dsi_msleep(&ctx, desc->exit_sleep_delay_ms);

\tmipi_dsi_dcs_set_display_on_multi(&ctx);

\tmipi_dsi_msleep(&ctx, desc->display_on_delay_ms);""",
    )
    source = replace_once(
        source,
        """\tmipi_dsi_dcs_set_display_off_multi(&ctx);
\tmipi_dsi_msleep(&ctx, 20);

\tmipi_dsi_dcs_enter_sleep_mode_multi(&ctx);
\tmipi_dsi_msleep(&ctx, 60);""",
        """\tmipi_dsi_dcs_set_display_off_multi(&ctx);
\tmipi_dsi_msleep(&ctx, panel->desc->display_off_delay_ms);

\tmipi_dsi_dcs_enter_sleep_mode_multi(&ctx);
\tmipi_dsi_msleep(&ctx, panel->desc->sleep_in_delay_ms);""",
    )

    source = replace_once(
        source,
        """static const struct panel_desc nt36672e_panel_desc = {
\t.display_mode = &nt36672e_1080x2408_60hz,
\t.width_mm = 74,
\t.height_mm = 131,
\t.mode_flags = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_LPM | MIPI_DSI_CLOCK_NON_CONTINUOUS,
\t.format = MIPI_DSI_FMT_RGB888,
\t.lanes = 4,
\t.panel_name = "nt36672e fhd plus panel",
\t.init_sequence = nt36672e_1080x2408_60hz_init,
};""",
        """static const struct panel_desc nt36672e_panel_desc = {
\t.supply_names = regulator_names,
\t.num_supplies = ARRAY_SIZE(regulator_names),
\t.display_mode = &nt36672e_1080x2408_60hz,
\t.width_mm = 74,
\t.height_mm = 131,
\t.mode_flags = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_LPM | MIPI_DSI_CLOCK_NON_CONTINUOUS,
\t.format = MIPI_DSI_FMT_RGB888,
\t.lanes = 4,
\t.panel_name = "nt36672e fhd plus panel",
\t.init_sequence = nt36672e_1080x2408_60hz_init,
\t.power_on_delay_ms = 0,
\t.reset_high_delay_ms = 10,
\t.reset_low_delay_ms = 10,
\t.reset_final_high_delay_ms = 10,
\t.display_off_delay_ms = 20,
\t.sleep_in_delay_ms = 60,
\t.exit_sleep_delay_ms = 120,
\t.display_on_delay_ms = 100,
};

static const char * const gemini_regulator_names[] = {
\t"outp",
\t"outn",
};

static const struct drm_display_mode gemini_1080x2160_60hz = {
\t.name = "1080x2160",
\t.clock = 138839,
\t.hdisplay = 1080,
\t.hsync_start = 1090,
\t.hsync_end = 1132,
\t.htotal = 1174,
\t.vdisplay = 2160,
\t.vsync_start = 2163,
\t.vsync_end = 2178,
\t.vtotal = 2188,
\t.flags = 0,
};

static const struct panel_desc gemini_panel_desc = {
\t.supply_names = gemini_regulator_names,
\t.num_supplies = ARRAY_SIZE(gemini_regulator_names),
\t.display_mode = &gemini_1080x2160_60hz,
\t/* 5.99in diagonal specification, converted from the 2:1 active area. */
\t.width_mm = 68,
\t.height_mm = 136,
\t.mode_flags = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_VIDEO_BURST |
\t\t\tMIPI_DSI_MODE_LPM | MIPI_DSI_CLOCK_NON_CONTINUOUS,
\t.format = MIPI_DSI_FMT_RGB888,
\t.lanes = 4,
\t.panel_name = "Gemini NT36672 1080x2160 panel",
\t.init_sequence = nt36672e_gemini_1080x2160_init,
\t.power_on_delay_ms = 20,
\t.reset_high_delay_ms = 10,
\t.reset_low_delay_ms = 10,
\t.reset_final_high_delay_ms = 20,
\t.display_off_delay_ms = 50,
\t.sleep_in_delay_ms = 120,
\t.exit_sleep_delay_ms = 120,
\t.display_on_delay_ms = 10,
};""",
    )
    source = replace_once(
        source,
        """\tfor (i = 0; i < ARRAY_SIZE(ctx->supplies); i++) {
\t\tctx->supplies[i].supply = regulator_names[i];
\t\tctx->supplies[i].init_load_uA = regulator_enable_loads[i];
\t}

\tret = devm_regulator_bulk_get(dev, ARRAY_SIZE(ctx->supplies),
\t\t\tctx->supplies);""",
        """\tif (!ctx->desc->supply_names ||
\t    ctx->desc->num_supplies > ARRAY_SIZE(ctx->supplies))
\t\treturn -EINVAL;

\tfor (i = 0; i < ctx->desc->num_supplies; i++) {
\t\tctx->supplies[i].supply = ctx->desc->supply_names[i];
\t\tctx->supplies[i].init_load_uA = regulator_enable_loads[i];
\t}

\tret = devm_regulator_bulk_get(dev, ctx->desc->num_supplies,
\t\t\t\t      ctx->supplies);""",
    )
    source = replace_once(
        source,
        """\t{
\t\t.compatible = "novatek,nt36672e",
\t\t.data = &nt36672e_panel_desc,
\t},
\t{ }""",
        """\t{
\t\t.compatible = "novatek,nt36672e",
\t\t.data = &nt36672e_panel_desc,
\t},
\t{
\t\t.compatible = "planet,gemini-pda-nt36672",
\t\t.data = &gemini_panel_desc,
\t},
\t{ }""",
    )

    source_path.write_text(source)
    print(f"updated {source_path} ({len(source)} bytes)")


if __name__ == "__main__":
    main()
