# Video Watermark & Text Remover Tool

A powerful desktop application built with PyQt5 and OpenCV to remove watermarks and text from video files.

## Features

✨ **Full-Featured UI**
- Intuitive PyQt5 interface
- Real-time video preview
- Frame-by-frame navigation
- Visual mask overlay display

🎬 **Video Processing**
- Support for MP4 videos
- Multiple removal methods (Inpaint, Morphological)
- Progress tracking during processing
- Multi-threaded processing (non-blocking UI)

🎯 **Selection Tools**
- Draw rectangles on video to mark watermarks/text
- Visual preview while drawing
- Clear and redraw selections
- Show/hide selection overlay

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Navigate to the project directory:**
   ```bash
   cd c:\Users\Mohit.m\Downloads\AVLR
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Load a video:**
   - Click "Load Video" button
   - Select an MP4 file from your storage

3. **Mark watermarks:**
   - Click and drag on the video to draw rectangles around watermarks
   - Use the frame slider to navigate through the video
   - Click "Show/Hide Selection" to see the mask overlay

4. **Process:**
   - Click "Process Video" button
   - Choose output location and filename
   - Wait for processing to complete
   - Your edited video will be saved

## How It Works

### Watermark Removal
- **Inpaint Method**: Uses advanced inpainting algorithms to intelligently reconstruct removed regions
- **Morphological Method**: Uses image morphology to remove selected areas

### Workflow
1. Load video file
2. Preview frames using the slider
3. Draw rectangular selections around watermarks/text
4. Process entire video with selected regions
5. Save processed video to your storage

## Tips

- ✅ Use the frame slider to find all watermark locations in the video
- ✅ Mark all watermarks before processing
- ✅ Inpaint method usually gives better results
- ✅ Processing time depends on video length and resolution
- ✅ All original files are preserved; processed video is saved separately

## Supported Formats

- Input: MP4
- Output: MP4

## System Requirements

- Windows/Mac/Linux
- 4GB RAM (minimum)
- Dual-core processor
- 500MB free disk space

## Troubleshooting

**"Failed to open video file"**
- Ensure file is a valid MP4 video
- Check file path contains no special characters

**Slow processing**
- Processing time scales with video length and resolution
- High-resolution videos take longer
- Consider using a lower resolution version for testing

**Poor watermark removal**
- Try the other removal method
- Ensure you've marked all watermark locations
- Use Inpaint method for better results

## License

This tool is provided as-is for personal use.

## Support

For issues or questions, refer to the OpenCV documentation:
- https://docs.opencv.org/
- https://www.pyqt.io/

---

**Made with ❤️ using OpenCV and PyQt5**
