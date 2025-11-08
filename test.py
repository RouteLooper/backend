import pandas as pd
import folium
import branca.colormap as cm

# Load SPT osm (CSV-formatted)
df = pd.read_csv("graphhopper-local/spt.json")

# Create base map centered near Cheltenham
m = folium.Map(location=[df.latitude.mean(), df.longitude.mean()],
               zoom_start=14, tiles="cartodb positron")

# Normalize distances for color mapping
min_d, max_d = df["distance"].min(), df["distance"].max()

# Create a color scale (handle older branca versions)
try:
    colormap = cm.linear.Viridis_09.scale(min_d, max_d)
except AttributeError:
    colormap = cm.linear.viridis.scale(min_d, max_d)  # fallback

colormap.caption = "Distance from Origin (m)"
colormap.add_to(m)

# Add each point with color based on distance
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row.latitude, row.longitude],
        radius=4,
        color=colormap(row.distance),
        fill=True,
        fill_opacity=0.8,
        popup=f"Distance: {row.distance:.1f} m\nTime: {row.time} ms"
    ).add_to(m)

# Save map
m.save("spt_colormap.html")
print("✅ Map saved to spt_colormap.html")
