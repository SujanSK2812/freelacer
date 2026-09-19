# Video Directory for Freelancer Portal

Place your video files here so they can be served by Django:

1. **Freelancer Guide Video**:
   - File name: `freelancer_guide.mp4`
   - Referenced in: `templates/home/index.html` (Freelancer Dashboard)
   - Path: `static/videos/freelancer_guide.mp4`

2. **Landing Page Video**:
   - File name: `landing_intro.mp4`
   - Referenced in: `templates/home/index.html` (Public Landing Page)
   - Path: `static/videos/landing_intro.mp4`

Supported formats: `.mp4`, `.webm`, `.mov`.
If you prefer to embed a YouTube or Vimeo video, you can replace the `<video>` tag in `templates/home/index.html` with an `<iframe>` embed (examples are provided directly in comments in `templates/home/index.html`).
