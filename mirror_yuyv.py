import numpy as np

def horizontally_mirror_yuv2(image_path, output_path, width, height):
    with open(image_path, 'rb') as f:
        yuv_data = np.frombuffer(f.read(), dtype=np.uint8)

    # Reshape the data to match the YUV2 format
    yuv_data = yuv_data.reshape((height, width * 2))

    # Mirror each row horizontally
    mirrored_yuv_data = np.zeros_like(yuv_data)
    for row in range(height):
        for col in range(0, width * 2, 4):
            col_inv = width * 2 - 4 - col
            y0, u, y1, v = yuv_data[row, col_inv:col_inv+4]
            mirrored_yuv_data[row, col:col+4] = y1, u, y0, v

    with open(output_path, 'wb') as f:
        f.write(mirrored_yuv_data.tobytes())

import sys
input_image_path = sys.argv[1]
output_image_path = sys.argv[2]
image_width = 640
image_height = 480

horizontally_mirror_yuv2(input_image_path, output_image_path, image_width, image_height)
