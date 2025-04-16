import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from PIL import Image

# --- Load and display logo ---
logo = Image.open('Forest Surveys Logo M.png')
st.image(logo, width=120)

st.title("EPUK Plot Upscaler Tool")

# Upload file
uploaded_file = st.file_uploader("Upload a .EPUK file", type=["EPUK"])

# Plot size inputs
input_area = st.number_input("Original plot size (ha)", value=0.0302, format="%.4f")
output_area = st.number_input("Desired plot size (ha)", value=0.05, format="%.4f")

if uploaded_file and input_area > 0 and output_area > input_area:
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()

    plot_data = []
    tree_data = []

    for line in lines:
        parts = line.strip().split(',')
        if parts[0] == 'P':
            plot_data.append(parts)
        elif parts[0] == 'M':
            tree_data.append(parts)

    plot_df = pd.DataFrame(plot_data, columns=["Type", "PlotID", "SubCompartment", "PlotNumber", "PlotSize", "Lat", "Long"])
    tree_df = pd.DataFrame(tree_data, columns=["Type", "PlotID", "Species", "DBH_mm", "Height_m"])

    tree_df[["PlotID", "Species", "DBH_mm", "Height_m"]] = tree_df[["PlotID", "Species", "DBH_mm", "Height_m"]].apply(pd.to_numeric)
    plot_df["PlotSize"] = pd.to_numeric(plot_df["PlotSize"])

    scale_factor = output_area / input_area
    simulated_tree_entries = []

    for plot_id in plot_df["PlotID"].astype(int).unique():
        plot_trees = tree_df[tree_df["PlotID"] == plot_id]
        species_counts = plot_trees["Species"].value_counts()

        for species, count in species_counts.items():
            subset = plot_trees[(plot_trees["Species"] == species)]
            count_needed = int(round(count * scale_factor)) - count
            if count_needed <= 0:
                continue

            valid = subset[subset["DBH_mm"] >= 70]
            if valid.shape[0] < 2:
                continue

            dbh_mean, dbh_std = valid["DBH_mm"].mean(), valid["DBH_mm"].std()
            ht_mean, ht_std = valid["Height_m"].mean(), valid["Height_m"].std()
            dbh_min, dbh_max = valid["DBH_mm"].min(), valid["DBH_mm"].max()

            dbh_samples = np.random.normal(dbh_mean, dbh_std, size=count_needed)
            ht_samples = np.random.normal(ht_mean, ht_std, size=count_needed)

            dbh_samples = np.clip(dbh_samples, dbh_min, dbh_max)
            ht_samples = np.clip(ht_samples, 1, None)

            for dbh, ht in zip(dbh_samples, ht_samples):
                if not np.isnan(dbh) and not np.isnan(ht):
                    line = f"M,{plot_id},{species},{int(round(dbh))},{int(round(ht))}\n"
                    simulated_tree_entries.append(line)

    # Update plot size in the P lines
    updated_plot_lines = []
    for row in plot_data:
        if row[0] == "P":
            row[4] = f"{output_area:.4f}"
        updated_plot_lines.append(",".join(row) + "\n")

    # Convert original tree lines
    original_tree_lines = tree_df.apply(
        lambda row: f"M,{row['PlotID']},{row['Species']},{int(row['DBH_mm'])},{int(row['Height_m'])}\n", axis=1
    ).tolist()

    # Assemble full output
    header = lines[0] + "\n"
    all_lines = header + "".join(updated_plot_lines + original_tree_lines + simulated_tree_entries)

    # Download button
    st.download_button(
        label="📁 Download Adjusted .EPUK File",
        data=all_lines,
        file_name="EPUK_Extrapolated_Updated.EPUK",
        mime="text/plain"
    )
