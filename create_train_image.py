#!/usr/bin/env python
# -*- coding:utf-8 -*-

import matplotlib
import os
import random
import sys
import time
import traceback

from datetime import datetime
from randimage import get_random_image, show_array

try:
    from PIL import Image
except ImportError:
    import Image


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


def strip_image_file(image_file):
    img = Image.open(image_file)
    return strip_image(img)


def refine_image(img, size):
    new_img = strip_image(img)
    return new_img.resize(size)


def refine_image_file(image_file, size):
    img = Image.open(image_file)
    return refine_image(img, size)


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


def reduce(img_path1, img_path2, size1, size2, angle, padding, direction, alpha_factor=100):
    img1 = load_image(img_path1)
    img2 = load_image(img_path2)

    img3 = refine_image(img1, size1)
    img4 = refine_image(img2, size2)

    img5 = concat(img3, img4, padding, direction)
    img6 = img5.rotate(angle, expand=True)

    img = strip_image(img6)
    if alpha_factor < 100:
        adjust_alpha(img, alpha_factor)

    return img


def create_random_image(width, height, max_width=100, max_height=100):
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


def combine(background, overlay, left, top):
    new_overlay = Image.new('RGBA', background.size)
    new_overlay.paste(overlay, (left, top), mask=overlay)

    img = Image.alpha_composite(background, new_overlay)
    return img


def combine_image_files(saved_path, img_path1, img_path2, config):
    bg_size = config['background-size']
    background = create_random_image(bg_size[0], bg_size[1])

    image_sizes = config['image-sizes']
    img_size1 = image_sizes[0]
    img_size2 = image_sizes[1]

    angle = config['angle']
    padding = config['padding']
    direction = config['direction']
    alpha_factor = config['alpha']

    overlay = reduce(img_path1, img_path2, img_size1, img_size2, angle, padding, direction, alpha_factor)

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


def test(img_path1, img_path2, saved_img_path, saved_config_path):
    config = dict()
    config['id'] = 1
    config['name'] = 'a lovely dog'
    config['background-size'] = (400, 400)
    config['image-sizes'] = [(40, 60), (80, 80)]
    config['angle'] = 150
    config['padding'] = 15
    config['direction'] = 'vertical'
    config['alpha'] = 80
    config['overlay-start'] = (100, 200)

    img, rect = combine_image_files(saved_img_path, img_path1, img_path2, config)
    img.show()

    save_config_as_yolo(saved_config_path, rect, config)


def main(argv):
    os.environ['TZ'] = 'Asia/Shanghai'
    time.tzset()

    try:
        print('Now: ', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        test(argv[1], argv[2], argv[3], argv[4])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('Error occurs at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__ == '__main__':
    main(sys.argv)
