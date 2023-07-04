import tkinter as tk
import webbrowser

from tkintermapview import TkinterMapView
import pysheds
import matplotlib.pyplot as plt
from pysheds.grid import Grid
import rasterio
import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt
import pandas as pd
from rasterio.features import rasterize
from shapely.geometry import Polygon
from rasterio.transform import xy
import pyproj
from shapely.geometry import Polygon, Point
import matplotlib.colors as colors
from matplotlib.cm import get_cmap
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
import matplotlib.ticker as ticker
def open_google_earth():
   
    # Construct the Google Earth URLs with the coordinates
    urls = ["https://earth.google.com/web/@39.45787982,-0.89850478,745.19483167a,360511.30776275d,35y,0h,0t,0r"]
    # Open Google Earth URLs in a web browser
    for url in urls:
        webbrowser.open(url)


def add_entry_pair():
    # Create a new set of X and Y entry fields
    frame_entry = tk.Frame(frame_entries)
    frame_entry.pack(pady=5)

    label_latitude = tk.Label(frame_entry, text="Lat.:")
    label_latitude.pack(side=tk.LEFT)

    entry_x = tk.Entry(frame_entry)
    entry_x.pack(side=tk.LEFT)

    label_longitude = tk.Label(frame_entry, text="Long.:")
    label_longitude.pack(side=tk.LEFT)

    entry_y = tk.Entry(frame_entry)
    entry_y.pack(side=tk.LEFT)

    # Store the entry fields in the entry_pairs list
    entry_pairs.append((entry_x, entry_y))
    
def draw():
   
    for entry_x, entry_y in entry_pairs:
        lat=float(entry_x.get())
        lon=float(entry_y.get())
        marker = map_widget.set_marker( lat,lon)
        map_widget.set_position(lat, lon)
        map_widget.set_zoom(15)
        
def dem():
    f = tk.filedialog.askopenfilename(filetypes=[("TIF files", ".tif")], title="Open DEM file (.tif)") 
    # Read the digital elevation model (DEM) using pysheds
    dem =  Grid.from_raster(f, data_name='dem')
    dem.fill_depressions(data='dem',out_name='flooded_dem')
    dem.resolve_flats(data='flooded_dem', out_name='inflated_dem')
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    dem.flowdir(data='inflated_dem', dirmap=dirmap, out_name='flowdir')
    dem.accumulation(data='flowdir', dirmap=dirmap, out_name='acc', pad_inplace=False)
    dem.flowdir[dem.flowdir == -1] = 0
    
    with rasterio.open(f) as src:
       # Read the elevation data as a numpy array
       elevation = src.read(1)
       shape = src.shape
       # Get the metadata for coordinate transformation
       transform = src.transform
       
       # Get the EPSG code of the source CRS
       source_crs = src.crs
       target_epsg = int(source_crs.to_epsg())
       source_epsg=4326
    pol=[]
    for entry_x, entry_y in entry_pairs:
       lat=float(entry_x.get())
       lon=float(entry_y.get())
       transformer = pyproj.Transformer.from_crs(f"EPSG:{source_epsg}", f"EPSG:{target_epsg}",
                                                 always_xy=True)
       # Perform the coordinate transformation
       transformed_x, transformed_y = transformer.transform(lon, lat)
       pol.append([transformed_x, transformed_y])
    
    polygon = Polygon(pol)  
    # Create a mask for the polygon on the fdir data
    mask = rasterize([polygon], out_shape=shape, fill=0, transform=transform)
    # Apply the mask to the fdir data, setting the selected pixels to zero
    dem.acc[mask == 1] = 0   
    
    interval_distance=int(entry_space.get())
    # Extract the coordinates of the polygon's exterior ring
    exterior_coords = polygon.exterior.coords
    # Calculate the perimeter of the polygon
    perimeter = polygon.length
    # Calculate the number of segments needed to cover the perimeter at the desired interval distance
    num_segments = int(perimeter / interval_distance)
    # Initialize a list to store the selected coordinates
    selected_coordinates = []

    # Iterate along the perimeter and sample points at the desired interval distance
    for i in range(num_segments + 1):
        # Calculate the distance along the perimeter
        distance_along_perimeter = i * interval_distance
        
        # Normalize the distance to be within the perimeter length
        normalized_distance = distance_along_perimeter % perimeter
        
        # Find the corresponding point on the boundary
        for j in range(len(exterior_coords) - 1):
            point1 = Point(exterior_coords[j])
            point2 = Point(exterior_coords[j + 1])
            segment_length = point1.distance(point2)
            
            if normalized_distance <= segment_length:
                segment_ratio = normalized_distance / segment_length
                x = exterior_coords[j][0] + (exterior_coords[j + 1][0] - exterior_coords[j][0]) * segment_ratio
                y = exterior_coords[j][1] + (exterior_coords[j + 1][1] - exterior_coords[j][1]) * segment_ratio
                selected_coordinates.append((x, y))
                break
                
            normalized_distance -= segment_length
    selected_coordinates=pd.DataFrame(selected_coordinates, columns=['X','Y'])
    
    # Plot the result
    # Get a view and add 1 (to help with log-scaled colors)
    xp, yp = polygon.exterior.xy
    
    acc = dem.view('acc', nodata=np.nan) + 1
    fig, ax = plt.subplots(figsize=(8,10))
    #im = ax.imshow(acc, extent=dem.extent, zorder=1,cmap='cubehelix',alpha=0.6, norm=colors.LogNorm(1, dem.acc.max()))
    ax.plot(xp, yp)
    ax.fill(xp, yp, alpha=0.3, label='Off-stream reservoir')
    len_path=[]
    # Generate a colormap
    cmap = get_cmap('tab10')
    for k in range (0,len(selected_coordinates)):
       
       # Get the coordinates of the origin point
       x, y = selected_coordinates.at[k,'X'], selected_coordinates.at[k,'Y']
       # Get the pixel coordinates of the origin
       X,Y = rasterio.transform.rowcol(transform, x, y)
       origin_pixel = rasterio.transform.rowcol(transform, x, y)
       origin_row, origin_col = origin_pixel[0],origin_pixel[1]
       
       'PATH'

       # Select the path by checking neighboring pixels with higher values
       path = []
       current_row, current_col = origin_row, origin_col
       while True:
          path.append((current_row, current_col))
          neighbors = dem.acc[
               current_row - 1 : current_row + 2,
               current_col - 1 : current_col + 2
               ]
           
          if len(neighbors) == 0:
            # neighbors is empty, go to the next k (loop)
            break
        
          try:
            max_idx = np.unravel_index(np.argmax(neighbors), neighbors.shape)
            max_row, max_col = current_row - 1 + max_idx[0], current_col - 1 + max_idx[1]
          except ValueError:
            # ValueError occurs when neighbors is empty or contains only NaN values
            # Go to the next k (loop)
            break

          if dem.acc[max_row, max_col] <= dem.acc[current_row, current_col]:
            break

          current_row, current_col = max_row, max_col
         
       path=pd.DataFrame(path, columns=['row','column'])
       len_path.append([x,y,len(path)])
       
       path['X'], path['Y'] = xy(transform, path['row'], path['column'])
       #path.to_csv('path_{},{}.csv'.format(x,y))
           
       # Get color from colormap
       color = cmap(k % cmap.N)
       
       ax.plot(path['X'], path['Y'], zorder=3, c=color)
       ax.scatter(selected_coordinates['X'], selected_coordinates['Y'],
                  zorder=1, s=30,marker='x', c='black')
    #plt.colorbar(im, ax=ax, label='Upstream Cells')
    plt.legend(fontsize=14)
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.grid()
   
    
   # Create frame for plot canvas
    plot_frame = tk.Frame(content_frame)
    plot_frame.grid(row=1, column=1, padx=10, pady=10)
    canvas = FigureCanvasTkAgg(fig, master = plot_frame)  
    canvas.draw()
    canvas.get_tk_widget().pack()
    len_path=round(pd.DataFrame(len_path,columns=['x_origin','y_origin','lenght']),2)
    print(len_path)
  
    
    
    
    
    '''res_frame = tk.Frame(content_frame)
    res_frame.grid(row=1, column=0, padx=10, pady=10)
    for i in range (0,len(len_path)):
        tk.Label(res_frame, text=str(len_path.iloc[i,0])).grid(row=i, column=0)
        tk.Label(res_frame, text=str(len_path.iloc[i,1])).grid(row=i, column=1)
        tk.Label(res_frame, text=str(len_path.iloc[i,2])).grid(row=i, column=2)'''
       
        
        
        
# Create a Tkinter window
window = tk.Tk()
window.title("Location breach")
window.geometry("800x700")

# Create a main frame for the window
main_frame = tk.Frame(window)
main_frame.pack(fill=tk.BOTH, expand=True)
# Create a canvas with scrollbars
canvas = tk.Canvas(main_frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
# Create a vertical scrollbar
scrollbar_y = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

# Create a horizontal scrollbar
scrollbar_x = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=canvas.xview)
scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

# Configure the canvas to use the scrollbars
canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
# Create a frame to hold the content
content_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)
# Pack the content frame inside the canvas
content_frame.pack(fill=tk.BOTH, expand=True)


frame_entries = tk.Frame(content_frame)
frame_entries.grid(row=0, column=0, padx=10, pady=10)




# Create a set of initial X and Y entry fields

# Create a button to open Google Earth
button_open_earth = tk.Button(frame_entries, text="Open Google Earth", command=open_google_earth)
button_open_earth.pack(pady=10)


button_dem=tk.Button(frame_entries, text="Upload DEM", command=dem)
button_dem.pack(pady=5)

title=tk.Label(frame_entries, text='Location off-stream reservoir')
title.pack(side=tk.TOP)
entry_pairs = []
for _ in range(4):
    frame_entry = tk.Frame(frame_entries)
    frame_entry.pack(pady=5)

    label_latitude = tk.Label(frame_entry, text="Lat.:")
    label_latitude.pack(side=tk.LEFT)

    entry_x = tk.Entry(frame_entry)
    entry_x.pack(side=tk.LEFT)

    label_longitude = tk.Label(frame_entry, text="Lon.:")
    label_longitude.pack(side=tk.LEFT)

    entry_y = tk.Entry(frame_entry)
    entry_y.pack(side=tk.LEFT)

    entry_pairs.append((entry_x, entry_y))
    
def add_coordinates():
    file_path = tk.filedialog.askopenfilename(filetypes=[("csv files", ".csv")], title="Open csv file (.csv)")
    if file_path:
       try:
           df = pd.read_csv(file_path, delimiter=';')
           
           # Assuming the CSV file has two columns: 'entry_x' and 'entry_y'
           entry_x_values = df['lat']
           entry_y_values = df['lon']
           num_entries = len(entry_x_values)

           # Add extra entry fields if the number of coordinates exceeds the initial set of 4
           if num_entries > 4:
                extra_entries_needed = num_entries - 4
                for _ in range(extra_entries_needed):
                    add_entry_pair()

           for i, (entry_x, entry_y) in enumerate(entry_pairs):
               entry_x.delete(0, tk.END)
               entry_x.insert(tk.END, entry_x_values[i])
               entry_y.delete(0, tk.END)
               entry_y.insert(tk.END, entry_y_values[i])
                   
       except (IOError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
           print("Error reading CSV file:", e)

# Create a button to add more entry fields
button_add_entry = tk.Button(frame_entries, text="Add Entry", command=add_entry_pair)
button_add_entry.pack()

button_add_coor = tk.Button(frame_entries, text="Upload coordinates", command=add_coordinates)
button_add_coor.pack(side=tk.BOTTOM)



# Create a frame for map widget and button_open_earth
frame_map = tk.Frame(content_frame)
frame_map.grid(row=0, column=1, padx=10, pady=10)

# Create map widget
map_widget = TkinterMapView(frame_map, width=400, height=300, corner_radius=0)
map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga")
map_widget.pack(side=tk.TOP, anchor=tk.NE)
map_widget.set_position(38, -0.8)
map_widget.set_zoom(8)
# Create a button to add more entry fields
button_draw = tk.Button(frame_map, text="Draw coordinates", command=draw)
button_draw.pack()

space=tk.Label(frame_map, text="Space between points")
space.pack(side=tk.LEFT)
entry_space=tk.Entry(frame_map)
entry_space.pack(side=tk.LEFT)

# Start the Tkinter event loop
window.mainloop()
