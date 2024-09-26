import open3d as o3d
import numpy as np
from scipy.ndimage import gaussian_filter

def load_model(model_path, voxel_size=0.0005, number_of_points=1000000):
    model = o3d.io.read_triangle_mesh(model_path)
    model.compute_vertex_normals()
    pcd = model.sample_points_uniformly(number_of_points=number_of_points)
    if voxel_size > 1e-6:
        pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    return pcd

def align_models(source, target, threshold=0.0001, trans_init=np.identity(4)):
    print("Starting GICP alignment...")
    reg_p2p = o3d.pipelines.registration.registration_icp(
        source, target, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    print(f"GICP alignment complete! {reg_p2p.transformation=}")
    return reg_p2p.transformation

def compute_color_map(source, target, transformation, smoothed=True, sigma=0.75, percentile=100):
    source.transform(transformation)
    distances = np.asarray(source.compute_point_cloud_distance(target))
    
    if smoothed:
        grid_size = int(np.sqrt(len(distances)))
        distance_grid = distances[:grid_size**2].reshape((grid_size, grid_size))
        smoothed_distances = gaussian_filter(distance_grid, sigma=sigma).flatten()
    else:
        smoothed_distances = distances
    
    max_distance = np.percentile(smoothed_distances, percentile)
    colors = [[(d / max_distance),1 - (d / max_distance), 0] for d in distances]
    source.colors = o3d.utility.Vector3dVector(colors)
    return source

def save_result(source_colored, voxel_size=0.005):
    source_compressed = source_colored.voxel_down_sample(voxel_size=voxel_size)
    avg_dist = np.mean(source_compressed.compute_nearest_neighbor_distance())
    radius = 1 * avg_dist
    source_colored_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(source_compressed,
           o3d.utility.DoubleVector([radius, radius * 1.3]))
    source_colored_mesh.compute_vertex_normals()
    
    try:
        o3d.io.write_triangle_mesh("static/models/aligned_source.obj", source_colored_mesh)
    except Exception as e:
        print(f"Error saving OBJ file: {e}")

def main():
    # target_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_after/model.obj"
    # source_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_before/model.obj"
    source_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_after/model.obj"
    target_model_path = "/home/vorart/workspace/my_projects/IW_Skoltech_IW/symmetra/models/preview/afrodita_before/model.obj"

    source = load_model(source_model_path, voxel_size=0.0005, number_of_points=5000000)
    target = load_model(target_model_path, voxel_size=0.0005, number_of_points=5000000)

    trans_init = np.identity(4)
    transformation = align_models(source, target, trans_init=trans_init)
    source_colored = compute_color_map(source, target, transformation)
    # target.paint_uniform_color([0.5, 0.5, 0.5])

    # Create and configure the visualizer
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Model Comparison", width=800, height=600)
    vis.add_geometry(source_colored)
    # vis.add_geometry(target)  # Add the target without the material parameter

    save_result(source_colored)

    # Set rendering options
    opt = vis.get_render_option()
    opt.point_size = 2.5  # Increase point size
    opt.background_color = np.asarray([0, 0, 0])  # Black background
    opt.show_coordinate_frame = True  # Optional: show coordinate frame

    vis.run()
    vis.destroy_window()

if __name__ == "__main__":
    main()
