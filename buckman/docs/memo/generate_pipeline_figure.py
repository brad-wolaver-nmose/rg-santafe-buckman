"""Generate pipeline flow diagram (Steps 1–5) for the tech memo.

Produces a 5-box sequential flow diagram showing the Buckman Wellfield
depletion pipeline from data ingestion through final table generation.
Output: pipeline_flow_steps_1_5.png at 300 DPI.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# --- Configuration ---
BOX_WIDTH = 2.2
BOX_HEIGHT = 3.0
GAP = 0.6  # horizontal gap between boxes
ARROW_LEN = GAP
Y_CENTER = 0.0

# Colors
FILL_COLOR = "#D6EAF8"  # light blue
BORDER_COLOR = "#2C3E50"  # dark blue-gray
ARROW_COLOR = "#2C3E50"
TITLE_BG = "#2C3E50"
TITLE_FG = "white"

# Step definitions: (step_label, title, input, output, engine)
STEPS = [
    ("STEP 1", "Ingest Data", "IN:  CSV", "OUT: T1, T2", "Python"),
    ("STEP 2", "MODFLOW Files", "IN:  .wel", "OUT: .wel+nam", "Python"),
    ("STEP 3", "Run MODFLOW96", "IN:  .wel+nam", "OUT: .flx", "MODFLOW96"),
    ("STEP 4", "Post-Process", "IN:  .flx", "OUT: CY{YYYY}", "sfmodflx"),
    ("STEP 5", "Depletion Tbl", "IN:  CY{YYYY}", "OUT: T3,T4,T5", "Python"),
]

N = len(STEPS)

# --- Figure setup ---
total_width = N * BOX_WIDTH + (N - 1) * GAP
fig_width = total_width + 1.5  # margins
fig_height = BOX_HEIGHT + 1.5

fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
ax.set_xlim(-0.75, total_width + 0.75)
ax.set_ylim(Y_CENTER - BOX_HEIGHT / 2 - 0.75, Y_CENTER + BOX_HEIGHT / 2 + 0.75)
ax.set_aspect("equal")
ax.axis("off")

# Section heights within each box (top to bottom):
#   Title bar:  0.55 units
#   Subtitle:   0.40 units
#   Divider 1
#   I/O block:  0.80 units
#   Divider 2
#   Engine:     0.45 units
TITLE_H = 0.55
SUBTITLE_H = 0.40
IO_H = 0.80
ENGINE_H = 0.45
# remaining space is dividers / padding
SECTION_TOP = Y_CENTER + BOX_HEIGHT / 2

for i, (step_label, title, inp, out, engine) in enumerate(STEPS):
    x_left = i * (BOX_WIDTH + GAP)
    x_center = x_left + BOX_WIDTH / 2
    y_bottom = Y_CENTER - BOX_HEIGHT / 2

    # Main box outline
    rect = mpatches.FancyBboxPatch(
        (x_left, y_bottom),
        BOX_WIDTH,
        BOX_HEIGHT,
        boxstyle="round,pad=0.05",
        facecolor=FILL_COLOR,
        edgecolor=BORDER_COLOR,
        linewidth=1.5,
    )
    ax.add_patch(rect)

    # Title bar background
    title_rect = mpatches.FancyBboxPatch(
        (x_left, SECTION_TOP - TITLE_H),
        BOX_WIDTH,
        TITLE_H,
        boxstyle="round,pad=0.05",
        facecolor=TITLE_BG,
        edgecolor=BORDER_COLOR,
        linewidth=1.5,
    )
    ax.add_patch(title_rect)

    # Step label (in title bar)
    ax.text(
        x_center,
        SECTION_TOP - TITLE_H / 2,
        step_label,
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=TITLE_FG,
        family="sans-serif",
    )

    # Subtitle (descriptive name)
    y_subtitle = SECTION_TOP - TITLE_H - SUBTITLE_H / 2 - 0.05
    ax.text(
        x_center,
        y_subtitle,
        title,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=BORDER_COLOR,
        family="sans-serif",
    )

    # Divider line 1
    y_div1 = SECTION_TOP - TITLE_H - SUBTITLE_H - 0.1
    ax.plot(
        [x_left + 0.1, x_left + BOX_WIDTH - 0.1],
        [y_div1, y_div1],
        color=BORDER_COLOR,
        linewidth=0.8,
    )

    # I/O text
    y_io_top = y_div1 - 0.15
    ax.text(
        x_center,
        y_io_top,
        inp,
        ha="center",
        va="top",
        fontsize=8,
        color="#333333",
        family="monospace",
    )
    ax.text(
        x_center,
        y_io_top - 0.35,
        out,
        ha="center",
        va="top",
        fontsize=8,
        color="#333333",
        family="monospace",
    )

    # Divider line 2
    y_div2 = y_io_top - IO_H
    ax.plot(
        [x_left + 0.1, x_left + BOX_WIDTH - 0.1],
        [y_div2, y_div2],
        color=BORDER_COLOR,
        linewidth=0.8,
    )

    # Engine label
    y_engine = y_div2 - ENGINE_H / 2
    ax.text(
        x_center,
        y_engine,
        engine,
        ha="center",
        va="center",
        fontsize=8.5,
        fontstyle="italic",
        color=BORDER_COLOR,
        family="sans-serif",
    )

    # Arrow to next box
    if i < N - 1:
        ax.annotate(
            "",
            xy=(x_left + BOX_WIDTH + GAP, Y_CENTER),
            xytext=(x_left + BOX_WIDTH, Y_CENTER),
            arrowprops=dict(
                arrowstyle="-|>",
                color=ARROW_COLOR,
                lw=2,
                mutation_scale=15,
            ),
        )

# Save
output_path = "docs/memo/pipeline_flow_steps_1_5.png"
fig.savefig(
    output_path,
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
    edgecolor="none",
    pad_inches=0.2,
)
plt.close(fig)
print(f"Saved: {output_path}")
