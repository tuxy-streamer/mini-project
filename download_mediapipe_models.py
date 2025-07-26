import os
import sys
import mediapipe as mp
import cv2
import numpy as np
import json
import shutil
import platform
from pathlib import Path
import time

class MediaPipeDownloader:
    def __init__(self):
        # Set paths
        self.project_dir = Path(r"D:\#CodeBase\#Projects\mini-project")
        self.models_dir = self.project_dir / "mediapipe_models"
        self.testing_dir = self.project_dir / "model_testing"
        
        # Create directories
        self.models_dir.mkdir(exist_ok=True)
        self.testing_dir.mkdir(exist_ok=True)
        
        print(f"📁 Project Directory: {self.project_dir}")
        print(f"📦 Models Directory: {self.models_dir}")
        print(f"🧪 Testing Directory: {self.testing_dir}")
    
    def get_mediapipe_cache_dirs(self):
        """Get all possible MediaPipe cache directories"""
        system = platform.system()
        possible_dirs = []
        
        if system == "Windows":
            # Common Windows cache locations
            possible_dirs.extend([
                Path.home() / "AppData" / "Local" / "mediapipe",
                Path.home() / "AppData" / "Roaming" / "mediapipe", 
                Path.home() / ".mediapipe",
                Path(os.environ.get('TEMP', '')) / "mediapipe",
                Path(os.environ.get('LOCALAPPDATA', '')) / "mediapipe" if os.environ.get('LOCALAPPDATA') else None,
                # Site-packages location
                Path(mp.__file__).parent / "modules",
                # Python cache
                Path(sys.prefix) / "Lib" / "site-packages" / "mediapipe" / "modules"
            ])
        elif system == "Darwin":
            possible_dirs.extend([
                Path.home() / "Library" / "Caches" / "mediapipe",
                Path.home() / ".mediapipe"
            ])
        else:
            possible_dirs.extend([
                Path.home() / ".cache" / "mediapipe",
                Path.home() / ".mediapipe"
            ])
        
        # Filter out None values and return existing directories
        return [d for d in possible_dirs if d and d.exists()]
    
    def check_existing_models(self):
        """Check if models already exist in project directory"""
        print("\n🔍 Checking for existing models...")
        
        # Check for model files
        model_files = list(self.models_dir.glob("*.tflite"))
        config_file = self.testing_dir / "model_info.json"
        
        if model_files and config_file.exists():
            print(f"📋 Found {len(model_files)} model files:")
            total_size = 0
            for model_file in model_files:
                size_mb = model_file.stat().st_size / (1024*1024)
                total_size += size_mb
                print(f"   ✅ {model_file.name} ({size_mb:.1f} MB)")
            
            print(f"💾 Total size: {total_size:.1f} MB")
            
            # Ask user if they want to re-download
            print("\n⚠️  Models already exist!")
            choice = input("Do you want to re-download? (y/N): ").strip().lower()
            
            if choice not in ['y', 'yes']:
                print("✅ Using existing models. Proceeding to test...")
                return False  # Don't download
        
        return True  # Download needed
    
    def create_dummy_face(self):
        """Create a more realistic dummy face for testing"""
        print("🎨 Creating realistic dummy face for testing...")
        
        # Create a higher resolution image
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        
        # Face center and dimensions
        center_x, center_y = 400, 300
        face_width, face_height = 180, 220
        
        # Skin color (more realistic)
        skin_color = (220, 190, 160)
        
        # Face shape (more oval)
        cv2.ellipse(img, (center_x, center_y), (face_width, face_height), 0, 0, 360, skin_color, -1)
        
        # Add face shading for depth
        cv2.ellipse(img, (center_x - 20, center_y - 20), (face_width-20, face_height-20), 0, 0, 360, (210, 180, 150), -1)
        
        # Eyes - more detailed
        left_eye_center = (center_x - 60, center_y - 40)
        right_eye_center = (center_x + 60, center_y - 40)
        
        # Eye sockets (shadow)
        cv2.ellipse(img, left_eye_center, (35, 25), 0, 0, 360, (200, 170, 140), -1)
        cv2.ellipse(img, right_eye_center, (35, 25), 0, 0, 360, (200, 170, 140), -1)
        
        # Eye whites
        cv2.ellipse(img, left_eye_center, (25, 15), 0, 0, 360, (255, 255, 255), -1)
        cv2.ellipse(img, right_eye_center, (25, 15), 0, 0, 360, (255, 255, 255), -1)
        
        # Iris
        cv2.circle(img, left_eye_center, 12, (70, 120, 50), -1)
        cv2.circle(img, right_eye_center, 12, (70, 120, 50), -1)
        
        # Pupils
        cv2.circle(img, left_eye_center, 6, (0, 0, 0), -1)
        cv2.circle(img, right_eye_center, 6, (0, 0, 0), -1)
        
        # Light reflection in eyes
        cv2.circle(img, (left_eye_center[0] - 3, left_eye_center[1] - 3), 2, (255, 255, 255), -1)
        cv2.circle(img, (right_eye_center[0] - 3, right_eye_center[1] - 3), 2, (255, 255, 255), -1)
        
        # Eyebrows
        eyebrow_color = (120, 80, 40)
        # Left eyebrow
        pts = np.array([
            [left_eye_center[0] - 30, left_eye_center[1] - 25],
            [left_eye_center[0] + 30, left_eye_center[1] - 30],
            [left_eye_center[0] + 25, left_eye_center[1] - 20],
            [left_eye_center[0] - 25, left_eye_center[1] - 15]
        ], np.int32)
        cv2.fillPoly(img, [pts], eyebrow_color)
        
        # Right eyebrow
        pts = np.array([
            [right_eye_center[0] - 30, right_eye_center[1] - 30],
            [right_eye_center[0] + 30, right_eye_center[1] - 25],
            [right_eye_center[0] + 25, right_eye_center[1] - 15],
            [right_eye_center[0] - 25, right_eye_center[1] - 20]
        ], np.int32)
        cv2.fillPoly(img, [pts], eyebrow_color)
        
        # Nose - more detailed
        nose_color = (210, 180, 150)
        # Nose bridge
        cv2.ellipse(img, (center_x, center_y + 20), (8, 40), 0, 0, 360, nose_color, -1)
        
        # Nose tip
        nose_pts = np.array([
            [center_x, center_y + 40],
            [center_x - 15, center_y + 65],
            [center_x + 15, center_y + 65]
        ], np.int32)
        cv2.fillPoly(img, [nose_pts], nose_color)
        
        # Nostrils
        cv2.ellipse(img, (center_x - 8, center_y + 60), (4, 6), 0, 0, 360, (150, 120, 90), -1)
        cv2.ellipse(img, (center_x + 8, center_y + 60), (4, 6), 0, 0, 360, (150, 120, 90), -1)
        
        # Mouth - more realistic
        mouth_color = (180, 100, 100)
        cv2.ellipse(img, (center_x, center_y + 100), (40, 12), 0, 0, 180, mouth_color, -1)
        # Mouth line
        cv2.ellipse(img, (center_x, center_y + 100), (35, 8), 0, 0, 180, (140, 80, 80), 2)
        
        # Cheeks (subtle)
        cv2.ellipse(img, (center_x - 80, center_y + 30), (25, 35), 0, 0, 360, (200, 170, 140), -1)
        cv2.ellipse(img, (center_x + 80, center_y + 30), (25, 35), 0, 0, 360, (200, 170, 140), -1)
        
        # Chin definition
        cv2.ellipse(img, (center_x, center_y + 150), (60, 30), 0, 0, 180, (200, 170, 140), -1)
        
        return img
    
    def download_models(self):
        """Download MediaPipe models"""
        print("\n⬇️  Downloading MediaPipe models...")
        
        try:
            # Initialize components to trigger downloads
            print("   🔄 Initializing Face Detection (Short Range)...")
            face_detection_short = mp.solutions.face_detection.FaceDetection(
                model_selection=0,  # Short range
                min_detection_confidence=0.5
            )
            
            print("   🔄 Initializing Face Detection (Full Range)...")
            face_detection_full = mp.solutions.face_detection.FaceDetection(
                model_selection=1,  # Full range  
                min_detection_confidence=0.5
            )
            
            print("   🔄 Initializing Face Mesh...")
            face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
            
            print("   🔄 Initializing Face Mesh (Video)...")
            face_mesh_video = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=5,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            # Create dummy face and process to trigger downloads
            dummy_face = self.create_dummy_face()
            rgb_face = cv2.cvtColor(dummy_face, cv2.COLOR_BGR2RGB)
            
            print("   📥 Triggering model downloads...")
            face_detection_short.process(rgb_face)
            face_detection_full.process(rgb_face)
            face_mesh.process(rgb_face)
            face_mesh_video.process(rgb_face)
            
            print("   ✅ Models downloaded to MediaPipe cache")
            
            # Copy models to project directory
            self.copy_models_to_project()
            
            # Store components for testing
            self.components = {
                'face_detection_short': face_detection_short,
                'face_detection_full': face_detection_full,
                'face_mesh': face_mesh,
                'face_mesh_video': face_mesh_video
            }
            
            print("✅ Models successfully downloaded and copied!")
            return True
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
            return False
    
    def copy_models_to_project(self):
        """Copy models from MediaPipe cache to project directory"""
        print("\n📂 Copying models to project directory...")
        
        cache_dirs = self.get_mediapipe_cache_dirs()
        copied_files = []
        
        print(f"   🔍 Searching in {len(cache_dirs)} cache directories...")
        
        for cache_dir in cache_dirs:
            print(f"   📁 Checking: {cache_dir}")
            if cache_dir.exists():
                # Find all .tflite model files
                for file_path in cache_dir.rglob("*.tflite"):
                    if file_path.is_file():
                        # Create descriptive filename
                        relative_path = file_path.relative_to(cache_dir)
                        new_name = f"mediapipe_{relative_path.name}"
                        target_path = self.models_dir / new_name
                        
                        try:
                            shutil.copy2(file_path, target_path)
                            size_mb = file_path.stat().st_size / (1024*1024)
                            copied_files.append({
                                'name': new_name,
                                'size_mb': round(size_mb, 2),
                                'original_path': str(file_path),
                                'target_path': str(target_path)
                            })
                            print(f"   ✅ {new_name} ({size_mb:.1f} MB)")
                        except Exception as e:
                            print(f"   ❌ Failed to copy {file_path.name}: {e}")
        
        # If no models found in cache, search in site-packages
        if not copied_files:
            print("   🔍 No models in cache, searching site-packages...")
            mp_path = Path(mp.__file__).parent
            
            for file_path in mp_path.rglob("*.tflite"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(mp_path)
                    new_name = f"mediapipe_{relative_path.name}"
                    target_path = self.models_dir / new_name
                    
                    try:
                        shutil.copy2(file_path, target_path)
                        size_mb = file_path.stat().st_size / (1024*1024)
                        copied_files.append({
                            'name': new_name,
                            'size_mb': round(size_mb, 2),
                            'original_path': str(file_path),
                            'target_path': str(target_path)
                        })
                        print(f"   ✅ {new_name} ({size_mb:.1f} MB)")
                    except Exception as e:
                        print(f"   ❌ Failed to copy {file_path.name}: {e}")
        
        # Save model info
        model_info = {
            'mediapipe_version': mp.__version__,
            'python_version': sys.version.split()[0],
            'download_date': str(time.strftime('%Y-%m-%d %H:%M:%S')),
            'project_dir': str(self.project_dir),
            'models_dir': str(self.models_dir),
            'total_models': len(copied_files),
            'total_size_mb': sum(f['size_mb'] for f in copied_files),
            'models': copied_files,
            'cache_dirs_searched': [str(d) for d in cache_dirs]
        }
        
        info_file = self.testing_dir / "model_info.json"
        with open(info_file, 'w') as f:
            json.dump(model_info, f, indent=2)
        
        print(f"   📋 Model info saved: {info_file}")
        print(f"   📊 Total: {len(copied_files)} files, {model_info['total_size_mb']:.1f} MB")
    
    def test_models(self):
        """Test all models with dummy data"""
        print("\n" + "=" * 60)
        print("🧪 TESTING MODELS WITH DUMMY DATA")
        print("=" * 60)
        
        # Create test images
        dummy_face = self.create_dummy_face()
        rgb_face = cv2.cvtColor(dummy_face, cv2.COLOR_BGR2RGB)
        
        # Save test image for reference
        test_image_path = self.testing_dir / "test_dummy_face.jpg"
        cv2.imwrite(str(test_image_path), dummy_face)
        print(f"💾 Test image saved: {test_image_path}")
        
        test_results = {}
        
        # Test 1: Face Detection Short Range
        print("\n1️⃣ Testing Face Detection (Short Range)...")
        try:
            result = self.components['face_detection_short'].process(rgb_face)
            faces_count = len(result.detections) if result.detections else 0
            test_results['face_detection_short'] = {
                'status': 'PASS' if faces_count > 0 else 'FAIL',
                'faces_detected': faces_count
            }
            print(f"   📊 Faces detected: {faces_count}")
            print(f"   {'✅ PASS' if faces_count > 0 else '❌ FAIL'}")
            
            if result.detections:
                detection = result.detections[0]
                confidence = detection.score[0]
                print(f"   🎯 Confidence: {confidence:.3f}")
                
        except Exception as e:
            test_results['face_detection_short'] = {'status': 'ERROR', 'error': str(e)}
            print(f"   ❌ ERROR: {e}")
        
        # Test 2: Face Detection Full Range
        print("\n2️⃣ Testing Face Detection (Full Range)...")
        try:
            result = self.components['face_detection_full'].process(rgb_face)
            faces_count = len(result.detections) if result.detections else 0
            test_results['face_detection_full'] = {
                'status': 'PASS' if faces_count > 0 else 'FAIL',
                'faces_detected': faces_count
            }
            print(f"   📊 Faces detected: {faces_count}")
            print(f"   {'✅ PASS' if faces_count > 0 else '❌ FAIL'}")
            
        except Exception as e:
            test_results['face_detection_full'] = {'status': 'ERROR', 'error': str(e)}
            print(f"   ❌ ERROR: {e}")
        
        # Test 3: Face Mesh Static
        print("\n3️⃣ Testing Face Mesh (Static)...")
        try:
            result = self.components['face_mesh'].process(rgb_face)
            landmarks_count = len(result.multi_face_landmarks) if result.multi_face_landmarks else 0
            
            landmark_points = 0
            if result.multi_face_landmarks:
                landmark_points = len(result.multi_face_landmarks[0].landmark)
            
            test_results['face_mesh_static'] = {
                'status': 'PASS' if landmarks_count > 0 else 'FAIL',
                'faces_with_landmarks': landmarks_count,
                'landmark_points_per_face': landmark_points
            }
            print(f"   📊 Faces with landmarks: {landmarks_count}")
            print(f"   📍 Landmark points per face: {landmark_points}")
            print(f"   {'✅ PASS' if landmarks_count > 0 else '❌ FAIL'}")
            
        except Exception as e:
            test_results['face_mesh_static'] = {'status': 'ERROR', 'error': str(e)}
            print(f"   ❌ ERROR: {e}")
        
        # Test 4: Face Mesh Video
        print("\n4️⃣ Testing Face Mesh (Video)...")
        try:
            result = self.components['face_mesh_video'].process(rgb_face)
            landmarks_count = len(result.multi_face_landmarks) if result.multi_face_landmarks else 0
            
            test_results['face_mesh_video'] = {
                'status': 'PASS' if landmarks_count > 0 else 'FAIL',
                'faces_with_landmarks': landmarks_count
            }
            print(f"   📊 Faces with landmarks: {landmarks_count}")
            print(f"   {'✅ PASS' if landmarks_count > 0 else '❌ FAIL'}")
            
        except Exception as e:
            test_results['face_mesh_video'] = {'status': 'ERROR', 'error': str(e)}
            print(f"   ❌ ERROR: {e}")
        
        # Test 5: Model Files Verification
        print("\n5️⃣ Testing Model Files...")
        model_files = list(self.models_dir.glob("*.tflite"))
        json_files = list(self.testing_dir.glob("*.json"))
        
        test_results['model_files'] = {
            'status': 'PASS' if len(model_files) >= 2 else 'FAIL',  # At least 2 models
            'tflite_files': len(model_files),
            'config_files': len(json_files)
        }
        
        print(f"   📦 .tflite files: {len(model_files)}")
        print(f"   📋 .json files: {len(json_files)}")
        
        for model_file in model_files:
            size_mb = model_file.stat().st_size / (1024*1024)
            print(f"      • {model_file.name} ({size_mb:.1f} MB)")
        
        print(f"   {'✅ PASS' if len(model_files) >= 2 else '❌ FAIL'}")
        
        # Save test results
        test_results['test_date'] = str(time.strftime('%Y-%m-%d %H:%M:%S'))
        test_results['dummy_face_image'] = str(test_image_path)
        
        results_file = self.testing_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        print(f"\n📋 Test results saved: {results_file}")
        
        # Summary
        passed_tests = sum(1 for test in test_results.values() 
                          if isinstance(test, dict) and test.get('status') == 'PASS')
        total_tests = sum(1 for test in test_results.values() 
                         if isinstance(test, dict) and 'status' in test)
        
        print(f"\n📊 Test Summary: {passed_tests}/{total_tests} tests passed")
        
        return passed_tests == total_tests
    
    def cleanup(self):
        """Clean up MediaPipe components"""
        if hasattr(self, 'components'):
            for component in self.components.values():
                try:
                    component.close()
                except:
                    pass
    
    def run(self):
        """Main execution flow"""
        print("=" * 70)
        print("MediaPipe Models Downloader & Tester")
        print("=" * 70)
        
        try:
            # Step 1: Check existing models
            need_download = self.check_existing_models()
            
            # Step 2: Download if needed
            if need_download:
                if not self.download_models():
                    print("❌ Download failed. Exiting.")
                    return False
            else:
                # Load existing components for testing
                print("\n🔄 Initializing components for testing...")
                dummy_face = self.create_dummy_face()
                rgb_face = cv2.cvtColor(dummy_face, cv2.COLOR_BGR2RGB)
                
                self.components = {
                    'face_detection_short': mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.3),
                    'face_detection_full': mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3),
                    'face_mesh': mp.solutions.face_mesh.FaceMesh(static_image_mode=True, min_detection_confidence=0.3),
                    'face_mesh_video': mp.solutions.face_mesh.FaceMesh(static_image_mode=False, min_detection_confidence=0.3)
                }
                
                # Warm up components
                for component in self.components.values():
                    component.process(rgb_face)
            
            # Step 3: Test models
            all_tests_passed = self.test_models()
            
            # Step 4: Final results
            print("\n" + "=" * 70)
            if all_tests_passed:
                print("🎉 ALL TESTS PASSED!")
                print("✅ MediaPipe models are working correctly")
                print("🚀 Ready for face recognition development!")
            else:
                print("⚠️  SOME TESTS FAILED!")
                print("🔧 Check the test results for details")
            
            print("=" * 70)
            print(f"📦 Models location: {self.models_dir}")
            print(f"🧪 Testing files location: {self.testing_dir}")
            print("💡 You can now use these models in your face recognition system")
            
            return all_tests_passed
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        
        finally:
            self.cleanup()

def main():
    """Main function"""
    downloader = MediaPipeDownloader()
    success = downloader.run()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Use the models in your face recognition system")
        print("2. Check model_testing/test_results.json for detailed test information")
        print("3. Reference the dummy face image in model_testing/ for testing")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check your internet connection")
        print("2. Ensure you have write permissions")
        print("3. Try running as administrator")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
