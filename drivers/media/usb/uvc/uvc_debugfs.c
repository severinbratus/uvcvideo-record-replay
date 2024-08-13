// SPDX-License-Identifier: GPL-2.0-or-later
/*
 *      uvc_debugfs.c --  USB Video Class driver - Debugging support
 *
 *      Copyright (C) 2011
 *          Laurent Pinchart (laurent.pinchart@ideasonboard.com)
 */

#include <linux/module.h>
#include <linux/debugfs.h>
#include <linux/slab.h>
#include <linux/usb.h>

#include "uvcvideo.h"

#define N_BLOBS_MAX 32

#define LAST_BLOB_WRAP (blob_wraps[n_blobs-1])

#define ADD_FSTORE_BLOB_FILE_AS_ARR(KEY) { \
    blob_wraps[n_blobs].data = (void *)(&fstore.KEY); \
    blob_wraps[n_blobs].size = sizeof(fstore.KEY); \
    n_blobs++; \
	debugfs_create_blob(#KEY, 0644, fstore_dir, &LAST_BLOB_WRAP); \
}

#define ADD_FSTORE_BLOB_FILE_AS_PTR(KEY, SIZE) { \
    blob_wraps[n_blobs].data = (void *)(fstore.KEY); \
    blob_wraps[n_blobs].size = SIZE; \
    n_blobs++; \
	debugfs_create_blob(#KEY, 0644, fstore_dir, &LAST_BLOB_WRAP); \
}


struct framestore fstore = {};

/* -----------------------------------------------------------------------------
 * Statistics
 */

#define UVC_DEBUGFS_BUF_SIZE	1024

struct uvc_debugfs_buffer {
	size_t count;
	char data[UVC_DEBUGFS_BUF_SIZE];
};

static int uvc_debugfs_stats_open(struct inode *inode, struct file *file)
{
	struct uvc_streaming *stream = inode->i_private;
	struct uvc_debugfs_buffer *buf;

	buf = kmalloc(sizeof(*buf), GFP_KERNEL);
	if (buf == NULL)
		return -ENOMEM;

	buf->count = uvc_video_stats_dump(stream, buf->data, sizeof(buf->data));

	file->private_data = buf;
	return 0;
}

static ssize_t uvc_debugfs_stats_read(struct file *file, char __user *user_buf,
				      size_t nbytes, loff_t *ppos)
{
	struct uvc_debugfs_buffer *buf = file->private_data;

	return simple_read_from_buffer(user_buf, nbytes, ppos, buf->data,
				       buf->count);
}

static int uvc_debugfs_stats_release(struct inode *inode, struct file *file)
{
	kfree(file->private_data);
	file->private_data = NULL;

	return 0;
}

static const struct file_operations uvc_debugfs_stats_fops = {
	.owner = THIS_MODULE,
	.open = uvc_debugfs_stats_open,
	.llseek = no_llseek,
	.read = uvc_debugfs_stats_read,
	.release = uvc_debugfs_stats_release,
};

/* -----------------------------------------------------------------------------
 * Global and stream initialization/cleanup
 */

static struct dentry *uvc_debugfs_root_dir;
static struct dentry *sb_dir;

void uvc_debugfs_init_stream(struct uvc_streaming *stream)
{
	struct usb_device *udev = stream->dev->udev;
	char dir_name[33];

	if (uvc_debugfs_root_dir == NULL)
		return;

	snprintf(dir_name, sizeof(dir_name), "%u-%u-%u", udev->bus->busnum,
		 udev->devnum, stream->intfnum);

	stream->debugfs_dir = debugfs_create_dir(dir_name,
						 uvc_debugfs_root_dir);

	debugfs_create_file("stats", 0444, stream->debugfs_dir, stream,
			    &uvc_debugfs_stats_fops);
}

void uvc_debugfs_cleanup_stream(struct uvc_streaming *stream)
{
	debugfs_remove_recursive(stream->debugfs_dir);
	stream->debugfs_dir = NULL;
}

/* Init & cleanup */

struct debugfs_blob_wrapper blob_wraps[N_BLOBS_MAX];
u8 n_blobs = 0;

u8 mode_switch = MODE_NORMAL;

void uvc_debugfs_init(void)
{
	uvc_debugfs_root_dir = debugfs_create_dir("uvcvideo", usb_debug_root);

	sb_dir = debugfs_create_dir("sb", uvc_debugfs_root_dir);
	if (sb_dir == NULL) {
		pr_emerg("uvc exc: no sb_dir!");
		return;
	}

	struct dentry* fstore_dir = debugfs_create_dir("framestore", sb_dir);

	debugfs_create_u8("n_segms", 0644, fstore_dir, &fstore.n_segms);

	// Each of these takes 20 * u32 at most

	ADD_FSTORE_BLOB_FILE_AS_ARR(segm_fmats);
	ADD_FSTORE_BLOB_FILE_AS_ARR(segm_nframes);
	ADD_FSTORE_BLOB_FILE_AS_ARR(offsets_fdata);
	ADD_FSTORE_BLOB_FILE_AS_ARR(offsets_fsizes);

	fstore.fdata = vmalloc(SIZE_FDATA);
	fstore.fsizes = (u32*)kzalloc(SIZE_FSIZES, GFP_KERNEL);

	ADD_FSTORE_BLOB_FILE_AS_PTR(fdata, SIZE_FDATA);
	ADD_FSTORE_BLOB_FILE_AS_PTR(fsizes, SIZE_FSIZES);

	debugfs_create_u8("index", 0644, sb_dir, &fstore.cur_segm_idx);
	debugfs_create_u8("switch", 0644, sb_dir, &mode_switch);
}

void uvc_debugfs_cleanup(void)
{
	debugfs_remove_recursive(uvc_debugfs_root_dir);

	vfree(fstore.fdata);
	kfree(fstore.fsizes);
}
