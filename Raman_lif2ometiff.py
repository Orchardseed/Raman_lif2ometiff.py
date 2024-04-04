from pathlib import Path
import numpy as np
import javabridge
import bioformats
import tifffile


# Update .lif file(s) or directory
lif_path = r'Path\to\input .lif or directory'
# Update output directory
output_dir = r'Path\to\output\directory'


def process_input_path(input_path, output_base_dir):
    input_path = Path(input_path)

    # If the input path is a .lif file, process this file
    if input_path.is_file() and input_path.suffix == '.lif':
        print(f"Processing file: {input_path}")
        process_raman_image_to_ometiff(input_path, output_base_dir)

    # If the input path is a directory, iterate through all .lif files in it
    elif input_path.is_dir():
        for lif_file in input_path.glob('*.lif'):
            print(f"Processing file: {lif_file}")
            process_raman_image_to_ometiff(lif_file, output_base_dir)
    else:
        print("The input path is neither a .lif file nor a directory containing .lif files.")


def process_raman_image_to_ometiff(lif_path, output_base_dir):
    lif_path = Path(lif_path)

    # Ensure the output directory exists
    output_base_dir = Path(output_base_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    # Create an output directory with the same name
    output_dir = output_base_dir / lif_path.stem

    # Check if the directory exists and append a number if it does
    counter = 1
    while output_dir.exists():
        output_dir = output_base_dir / f"{lif_path.stem}({counter})"
        counter += 1
    output_dir.mkdir()

    # Read metadata
    metadata = bioformats.get_omexml_metadata(path=str(lif_path))
    ome_xml = bioformats.OMEXML(metadata)
    num_series = ome_xml.get_image_count()
    print(f"Total series in file: {num_series}")

    # Open the .lif file
    with bioformats.ImageReader(str(lif_path), perform_init=True) as reader:
        for series_index in range(num_series):
            # Set the current series in the reader
            reader.rdr.setSeries(series_index)
            # print(series_index)

            # Get metadata for this series
            series_md = ome_xml.image(series_index)
            num_channels = series_md.Pixels.get_channel_count()
            size_t = series_md.Pixels.SizeT
            size_x = series_md.Pixels.SizeX
            size_y = series_md.Pixels.SizeY
            X = series_md.Pixels.PhysicalSizeX
            Y = series_md.Pixels.PhysicalSizeY
            print(
                f"Series {series_index} has channels: {num_channels}, X: {X},  Y: {X}, Size: ({size_x}, {size_y}), Raman shifts: {size_t}.")

            # For each series, iterate over each channel
            for channel_index in range(num_channels):

                # # Initialize a 3D numpy array to store all Raman shift data for the channel
                # np.uint8 here
                raman_shift_data = np.zeros((size_t, size_y, size_x), dtype=np.uint8)

                # For each channel, iterate over Raman shifts
                for t_index in range(size_t):
                    # Read the image slide
                    img_data = reader.read(t=t_index, c=channel_index, rescale=False)
                    raman_shift_data[t_index, :, :] = img_data

                # Define the path
                channel_name = series_md.Name if series_md.Name else f"Channel_{channel_index}"
                print(f"Raman shifts: {channel_name}")
                output_path = output_dir / f"Series_{series_index + 1}_Ch{channel_index + 1}_{channel_name}.ome.tiff"
                # print(raman_shift_data.shape)

                # Set Metadata
                ome_metadata = {'PhysicalSizeX': X, 'PhysicalSizeY': Y,
                                'Name': channel_name, 'AcquisitionDate': series_md.AcquisitionDate,
                                'axes': 'TYX'}
                # Save the image data as OME-TIFF
                tifffile.imwrite(str(output_path), raman_shift_data,
                                 compression='zlib', metadata=ome_metadata)
                print(f"Processed and saved as multi-page OME-TIFF: {output_path}")


# Initialize the JVM
javabridge.start_vm(class_path=bioformats.JARS)

# Convert .lif file(s) into a directory with the same name
process_input_path(lif_path, output_dir)

# Close the JVM
javabridge.kill_vm()
