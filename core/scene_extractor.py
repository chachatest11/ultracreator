"""
Scene detection and frame extraction for video analysis
"""
import os
import cv2
from typing import List, Dict, Optional, Callable
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector


def extract_scenes(
    video_path: str,
    output_dir: str,
    threshold: float = 27.0,
    min_scene_len: float = 0.5,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Extract scenes from video and save first/last frames of each scene

    Args:
        video_path: Path to video file
        output_dir: Directory to save extracted frames
        threshold: Scene detection sensitivity (lower = more sensitive, default 27.0)
        min_scene_len: Minimum scene length in seconds (default 0.5)
        progress_callback: Optional callback function for progress updates

    Returns:
        Dict with scene info and extracted frames
    """

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    if progress_callback:
        progress_callback("📹 비디오 분석 중...")

    # Initialize video manager and scene manager
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()

    # Add ContentDetector algorithm (detects cuts based on frame content changes)
    scene_manager.add_detector(
        ContentDetector(threshold=threshold, min_scene_len=int(min_scene_len * video_manager.get_framerate()))
    )

    # Start video manager
    video_manager.start()

    # Detect scenes
    scene_manager.detect_scenes(frame_source=video_manager)

    # Get list of detected scenes
    scene_list = scene_manager.get_scene_list()

    if progress_callback:
        progress_callback(f"✅ {len(scene_list)}개의 장면 감지됨")

    # Release video manager
    video_manager.release()

    if not scene_list:
        return {
            'success': False,
            'message': '장면을 감지하지 못했습니다. threshold 값을 조정해보세요.',
            'scenes': [],
            'frames': []
        }

    # Extract frames using OpenCV
    if progress_callback:
        progress_callback("🖼️ 프레임 추출 중...")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    extracted_frames = []

    for idx, (start_time, end_time) in enumerate(scene_list, 1):
        # Calculate frame numbers
        start_frame = int(start_time.get_frames())
        end_frame = int(end_time.get_frames())

        # Extract first frame of scene
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        ret, frame = cap.read()

        if ret:
            start_filename = f"scene_{idx:03d}_start.jpg"
            start_path = os.path.join(output_dir, start_filename)
            cv2.imwrite(start_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            extracted_frames.append({
                'scene': idx,
                'type': 'start',
                'path': start_path,
                'frame_num': start_frame,
                'time': start_time.get_seconds()
            })

        # Extract last frame of scene (one frame before next scene starts)
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(start_frame, end_frame - 1))
        ret, frame = cap.read()

        if ret:
            end_filename = f"scene_{idx:03d}_end.jpg"
            end_path = os.path.join(output_dir, end_filename)
            cv2.imwrite(end_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            extracted_frames.append({
                'scene': idx,
                'type': 'end',
                'path': end_path,
                'frame_num': end_frame - 1,
                'time': end_time.get_seconds()
            })

        if progress_callback and idx % 5 == 0:
            progress_callback(f"📸 {idx}/{len(scene_list)} 장면 처리 중...")

    cap.release()

    if progress_callback:
        progress_callback(f"✅ 총 {len(extracted_frames)}개 프레임 추출 완료!")

    # Build scene info
    scenes_info = []
    for idx, (start_time, end_time) in enumerate(scene_list, 1):
        scenes_info.append({
            'scene_num': idx,
            'start_time': start_time.get_seconds(),
            'end_time': end_time.get_seconds(),
            'duration': (end_time - start_time).get_seconds(),
            'start_frame': int(start_time.get_frames()),
            'end_frame': int(end_time.get_frames())
        })

    return {
        'success': True,
        'message': f'{len(scene_list)}개 장면에서 {len(extracted_frames)}개 프레임 추출 완료',
        'video_path': video_path,
        'output_dir': output_dir,
        'fps': fps,
        'total_scenes': len(scene_list),
        'total_frames': len(extracted_frames),
        'scenes': scenes_info,
        'frames': extracted_frames
    }


def get_scene_summary(result: Dict) -> str:
    """Generate a text summary of scene extraction results"""
    if not result.get('success'):
        return result.get('message', '추출 실패')

    scenes = result.get('scenes', [])

    summary = f"### 📊 장면 분석 결과\n\n"
    summary += f"- **총 장면 수**: {result['total_scenes']}개\n"
    summary += f"- **추출된 프레임**: {result['total_frames']}개 (각 장면당 시작/끝)\n"
    summary += f"- **저장 위치**: `{result['output_dir']}`\n\n"

    summary += "#### 장면 목록:\n\n"
    for scene in scenes[:10]:  # Show first 10 scenes
        summary += (
            f"- **Scene {scene['scene_num']}**: "
            f"{scene['start_time']:.1f}s ~ {scene['end_time']:.1f}s "
            f"(길이: {scene['duration']:.1f}s)\n"
        )

    if len(scenes) > 10:
        summary += f"\n... 및 {len(scenes) - 10}개 장면 더\n"

    return summary
