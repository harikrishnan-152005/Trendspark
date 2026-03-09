import osmnx as ox

location = "Tambaram, Tamil Nadu, India"
tags = {"amenity": ["restaurant", "cafe", "fast_food"]}

gdf = ox.features_from_place(location, tags)
print("Count:", len(gdf))