import open3d as o3d
import numpy as np
from scipy.ndimage import gaussian_filter
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def load_model(model_path, voxel_size=0.001):
    model = o3d.io.read_triangle_mesh(model_path)
    model.compute_vertex_normals()
    pcd = model.sample_points_uniformly(number_of_points=1000000)
    pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    return pcd

def align_models(source, target, threshold=0.0003, trans_init=np.identity(4)):
    print("Starting GICP alignment...")
    reg_p2p = o3d.pipelines.registration.registration_icp(
        source, target, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    print(f"GICP alignment complete! {reg_p2p.transformation=}")
    return reg_p2p.transformation

def compute_color_map(source, target, transformation, smoothed=True, sigma=0.85, percentile=100):
    source.transform(transformation)
    distances = np.asarray(source.compute_point_cloud_distance(target))
    
    if smoothed:
        grid_size = int(np.sqrt(len(distances)))
        distance_grid = distances[:grid_size**2].reshape((grid_size, grid_size))
        smoothed_distances = gaussian_filter(distance_grid, sigma=sigma).flatten()
    else:
        smoothed_distances = distances
    
    max_distance = np.percentile(smoothed_distances, percentile)
    smoothed_distances = np.clip(smoothed_distances, 0, max_distance)
    # norm = plt.Normalize(vmin=0, vmax=max_distance)
    # cmap = plt.colormaps.get_cmap('jet')  # Updated according to the deprecation warning
    # colors = cmap(norm(distances))[:, :3]  # Get RGB values from colormap
    colors = [[(d / max_distance),1 - (d / max_distance), 0] for d in distances]
    source.colors = o3d.utility.Vector3dVector(colors)
    return source

def save_result(source_colored, voxel_size=0.005):
    # Create a mesh from the colored point cloud for visualization
    source_compressed = source_colored.voxel_down_sample(voxel_size=voxel_size)
    avg_dist = np.mean(source_compressed.compute_nearest_neighbor_distance())
    radius = 1.3 * avg_dist
    source_colored_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(source_compressed,
           o3d.utility.DoubleVector([radius, radius * 1.3]))
    source_colored_mesh.compute_vertex_normals()
    
    # Updated the path and filename handling to prevent 'Write OBJ failed'
    try:
        o3d.io.write_triangle_mesh("static/models/aligned_source.obj", source_colored_mesh)
    except Exception as e:
        print(f"Error saving OBJ file: {e}")

def main():
    target_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_after/model.obj"
    source_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_before/model.obj"

    source = load_model(source_model_path)
    target = load_model(target_model_path)

    trans_init = np.identity(4)
    transformation = align_models(source, target, trans_init=trans_init)
    source_colored = compute_color_map(source, target, transformation)
    # target.paint_uniform_color([0.5, 0.5, 0.5])

    # save_result(source_colored)

    # Visualize results with enhanced settings
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Model Comparison", width=800, height=600)
    vis.add_geometry(source_colored)
    # vis.add_geometry(target)
    
    opt = vis.get_render_option()
    opt.point_size = 2.0  # Increase point size
    opt.background_color = np.asarray([0, 0, 0])  # Black background
    opt.show_coordinate_frame = True  # Optional: show coordinate frame

    vis.run()
    vis.destroy_window()

if __name__ == "__main__":
    main()
