#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import matplotlib
import os
import random
import stat
import sys
import time
import traceback
import yaml

from datetime import datetime
from randimage import get_random_image, show_array

try:
    from PIL import Image, ImageDraw
except ImportError:
    import Image


def mkdir(path,
          mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH):
    if not os.path.exists(path):
        os.mkdir(path, mode)

    chmod(path, mode)


def chmod(path,
          mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH):
    if os.path.exists(path):
        try:
            os.chmod(path, mode)
        except PermissionError as e:
            print(e)


def remove(path):
    if os.path.exists(path):
        os.remove(path)


def adjust_alpha(img, alpha_factor):
    # Check if the image has an alpha channel
    if img.mode != 'RGBA':
        return

    # Get the pixel data
    pixels = img.load()

    # Iterate through each pixel
    for i in range(img.width):
        for j in range(img.height):

            # Check if alpha is not 100% transparent
            if pixels[i, j][3] == 0:
                continue

            # Update the alpha value
            pixels[i, j] = pixels[i, j][:3] + (int(pixels[i, j][3] * alpha_factor / 100),)


def load_image(pathname):
    img = Image.open(pathname)

    # Check if the image has an alpha channel
    if img.mode == 'RGBA':
        return img

    return img.convert('RGBA')


def strip_image(img):
    left, top = img.size
    right, bottom = (0, 0)

    # Get the pixel data
    pixels = img.load()

    # Iterate through each pixel
    for i in range(img.width):
        for j in range(img.height):

            valid = False

            for v in pixels[i, j]:
                if v > 0:
                    valid = True
                    break

            if not valid:
                continue

            if left > i:
                left = i

            if top > j:
                top = j

            if right < i:
                right = i

            if bottom < j:
                bottom = j

    if left == 0 and top == 0 and right == img.size[0] and bottom == img.size[1]:
        return img

    new_img = Image.new('RGBA', (right - left, bottom - top))
    new_img.paste(img, (-1 * left, -1 * top), mask=img)

    return new_img


def refine_image(img, size, scale_by, scale_keeping_ratio):
    new_img = strip_image(img)

    w1, h1 = size
    if scale_keeping_ratio:
        w0, h0 = img.size

        if 'horizontal' == scale_by:
            h1 = int(h0 * w1 / w0)
        elif 'vertical' == scale_by:
            w1 = int(w0 * h1 / h0)

    return new_img.resize((w1, h1))


def concat_vertical(img1, img2, padding):
    width1, height1 = img1.size
    width2, height2 = img2.size

    if width1 > width2:
        width = width1
        left1 = 0
        left2 = int((width - width2) / 2)
    else:
        width = width2
        left1 = int((width - width1) / 2)
        left2 = 0

    height = height1 + padding + height2

    img = Image.new('RGBA', (width, height))
    img.paste(img1, (left1, 0), mask=img1)
    img.paste(img2, (left2, height1 + padding), mask=img2)

    return img


def concat_horizontal(img1, img2, padding):
    pass


def concat(img1, img2, padding, direction):
    if 'vertical' == direction:
        return concat_vertical(img1, img2, padding)

    return concat_horizontal(img1, img2, padding)


def reduce(img_path1, img_path2, size1, size2,
           scale_by, scale_keeping_ratio,
           angle, padding, direction, alpha_factor=100):
    img1 = load_image(img_path1)
    img2 = load_image(img_path2)

    img3 = refine_image(img1, size1, scale_by, scale_keeping_ratio)
    img4 = refine_image(img2, size2, scale_by, scale_keeping_ratio)

    img5 = concat(img3, img4, padding, direction)
    img6 = img5.rotate(angle, expand=True)

    img = strip_image(img6)
    if alpha_factor < 100:
        adjust_alpha(img, alpha_factor)

    return img


def create_random_complex_image(width, height, max_width=16, max_height=16):
    if width > max_width or height > max_height:
        size = (max_width, max_height)
        resize_needed = True
    else:
        size = (width, height)
        resize_needed = False

    img_array = get_random_image(size)  # returns numpy array

    pathname = 'image-{}-{}.png'.format(width, height)
    matplotlib.image.imsave(pathname, img_array)

    img = Image.open(pathname)

    if resize_needed:
        return img.resize((width, height))

    return img


def create_random_simple_image(width, height, max_number=10000):
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)

    # Generate and test random pixels
    for _ in range(max_number):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw.point((x, y), fill=color)

    return img


def combine(background, overlay, left, top):
    new_overlay = Image.new('RGBA', background.size)
    new_overlay.paste(overlay, (left, top), mask=overlay)

    img = Image.alpha_composite(background, new_overlay)
    return img


def combine_image_files(saved_dir, saved_path, img_path1, img_path2, config):
    background_type = config['background-type']
    bg_size = config['background-size']

    if 'image' == background_type:
        background_image = config['background-image']
        path_name = os.path.join(saved_dir, background_image)
        img = load_image(path_name)
        background = img.resize((bg_size[0], bg_size[1]))
    elif 'random-image' == background_type:
        background_random_image = config['background-random-image']
        if 'simple' == background_random_image:
            background = create_random_simple_image(bg_size[0], bg_size[1])
        elif 'complex' == background_random_image:
            background = create_random_complex_image(bg_size[0], bg_size[1])

    scale_by = config['scale-by']
    scale_keeping_ratio = config['scale-keeping-ratio']

    image_sizes = config['image-sizes']
    img_size1 = image_sizes[0]
    img_size2 = image_sizes[1]

    angle = config['angle']
    padding = config['padding']
    direction = config['direction']
    alpha_factor = config['alpha']

    overlay = reduce(img_path1, img_path2, img_size1, img_size2,
                     scale_by, scale_keeping_ratio,
                     angle, padding, direction, alpha_factor)

    pos = config['overlay-start']
    left = pos[0]
    top = pos[1]

    if left + overlay.width > background.width:
        left = background.width - overlay.width

    if top + overlay.height > background.height:
        top = background.height - overlay.height

    img = combine(background, overlay, left, top)
    img.save(saved_path)

    rect = (left, top, overlay.width, overlay.height)

    return img, rect


def save_config_as_yolo(yolo_path, rect, config):
    with open(yolo_path, 'w+') as fp:
        size = config['background-size']

        x = (rect[0] * 2 + rect[2]) / 2 / size[0]
        y = (rect[1] * 2 + rect[3]) / 2 / size[1]
        w = rect[2] / size[0]
        h = rect[3] / size[1]

        content = '{} {} {} {} {}'.format(config['id'], x, y, w, h)
        fp.write(content)


def save_config_files_as_yolo(dir_name, new_classes, start_index):
    classes_path = os.path.join(dir_name, 'labels/classes.txt')

    if os.path.exists(classes_path):
        with open(classes_path, 'r') as fp:
            classes = fp.read().split('\n')
    else:
        classes = list()

    existing_end_index = len(classes)
    end_index = start_index + len(new_classes)
    if existing_end_index >= end_index:
        for index in range(start_index, end_index):
            classes[index] = new_classes[index - start_index]
    else:
        if existing_end_index < start_index:
            empty_classes = ['' for _ in range(existing_end_index, start_index)]
            classes.extend(empty_classes)

        classes.extend(new_classes)

    with open(classes_path, 'w+') as fp:
        fp.write('\n'.join(classes))

    yaml_path = os.path.join(dir_name, 'data.yaml')
    data = {
        'path': 'ROOT-PATH',
        'train': 'images',
        'val': 'images',
        'names': classes
    }

    # 打开一个文件用于写入
    with open(yaml_path, 'w+') as fp:
        yaml.dump(data, fp)


def create_one(saved_dir, prefix, path_name1, path_name2, config, global_cfg):
    config['scale-by'] = global_cfg['scale-by']
    config['scale-keeping-ratio'] = global_cfg['scale-keeping-ratio']

    sizes = global_cfg['size-ranges']

    w1 = random.randint(sizes[0], sizes[1])
    h1 = random.randint(sizes[0], sizes[1])

    scale_simultaneously = global_cfg['scale-simultaneously']
    if not scale_simultaneously:
        w2 = random.randint(sizes[0], sizes[1])
        h2 = random.randint(sizes[0], sizes[1])
    else:
        w2 = w1
        h2 = h1

    size1 = (w1, h1)
    size2 = (w2, h2)
    config['image-sizes'] = [size1, size2]

    paddings = global_cfg['padding-ranges']
    config['padding'] = random.randint(paddings[0], paddings[1])

    alpha_factors = global_cfg['alpha-ranges']
    config['alpha'] = random.randint(alpha_factors[0], alpha_factors[1])

    angles = global_cfg['angles']
    config['angle'] = angles[random.randint(0, len(angles) - 1)]

    config['background-type'] = global_cfg['background-type']
    config['background-image'] = global_cfg['background-image']
    config['background-random-image'] = global_cfg['background-random-image']

    overlay_size = global_cfg['overlay-sizes']
    x = random.randint(overlay_size[0], overlay_size[1])
    y = random.randint(overlay_size[0], overlay_size[1])
    config['overlay-start'] = (x, y)

    basename = '{}-{}'.format(prefix, config['name'])

    image_path = os.path.join(saved_dir, 'images/{}.png'.format(basename))
    label_path = os.path.join(saved_dir, 'labels/{}.txt'.format(basename))

    img, rect = combine_image_files(saved_dir, image_path, path_name1, path_name2, config)
    save_config_as_yolo(label_path, rect, config)

    print('Save {}'.format(basename))


def create_group(saved_dir, index, dir_name1, dir_name2, config, global_cfg):
    path_names1 = get_image_files(dir_name1)
    path_names2 = get_image_files(dir_name2)

    if not path_names1 or not path_names2:
        return

    repeated_times = global_cfg['repeated-times']

    count = 0
    for path_name1 in path_names1:
        for path_name2 in path_names2:
            for i in range(repeated_times):
                prefix = str(index).zfill(4) + str(count).zfill(4)
                create_one(saved_dir, prefix, path_name1, path_name2, config, global_cfg)
                count += 1


def load_config(config_file):
    with open(config_file) as fp:
        return json.loads(fp.read())


def get_sub_dirs(dir_name):
    path_names = list()
    for filename in os.listdir(dir_name):

        pathname = os.path.join(dir_name, filename)
        if os.path.isdir(pathname):
            path_names.append(pathname)

    return path_names


def get_image_files(dir_name):
    def get_file_suffix(file_name):
        pos = file_name.rfind('.')

        if pos < 0:
            return ''

        return file_name[pos + 1:].lower()

    path_names = list()
    for filename in os.listdir(dir_name):

        pathname = os.path.join(dir_name, filename)
        if not os.path.isfile(pathname):
            continue

        suffix = get_file_suffix(filename)
        if suffix not in ['jpg', 'png', 'webp', 'jpeg']:
            continue

        path_names.append(pathname)

    return path_names


def create(config_file):
    saved_dir = os.path.dirname(config_file)

    mkdir(os.path.join(saved_dir, 'images'))
    mkdir(os.path.join(saved_dir, 'labels'))

    global_cfg = load_config(config_file)

    dir_names = global_cfg['dir-names']

    sub_dirs1 = get_sub_dirs(os.path.join(saved_dir, dir_names[0]))
    sub_dirs2 = get_sub_dirs(os.path.join(saved_dir, dir_names[1]))

    config = dict()

    background_size = global_cfg['background-size']
    direction = global_cfg['direction']

    config['background-size'] = background_size
    config['direction'] = direction

    index = global_cfg['index']
    names = []

    for sub_dir1 in sub_dirs1:
        for sub_dir2 in sub_dirs2:
            config['id'] = index
            name = '{}-{}'.format(os.path.basename(sub_dir1),
                                  os.path.basename(sub_dir2))
            config['name'] = name
            names.append(name)

            create_group(saved_dir, index, sub_dir1, sub_dir2, config, global_cfg)

            index += 1

    save_config_files_as_yolo(saved_dir, names, global_cfg['index'])

    print(len(names), 'names have been created.')


def main(argv):
    os.environ['TZ'] = 'Asia/Shanghai'
    time.tzset()

    if len(argv) < 2:
        print('Usage:\n\t', argv[0], 'CONFIG-PATH-NAME\n')
        return

    try:
        print('Now: ', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        create(argv[1])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('Error occurs at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__ == '__main__':
    main(sys.argv)
