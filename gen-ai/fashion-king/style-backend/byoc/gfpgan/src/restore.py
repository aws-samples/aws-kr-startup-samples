import cv2
import os
import torch
from basicsr.utils import imwrite
from gfpgan import GFPGANer

# 전역 변수로 GFPGAN 모델 설정
MODEL_PATH = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth'
restorer = GFPGANer(
    model_path=MODEL_PATH,
    upscale=2,
    arch='clean',
    channel_multiplier=2,
    bg_upsampler=None)

def restore_face(input_path, output_dir):
    """
    GFPGAN을 사용하여 얼굴 이미지를 복원하는 함수
    
    Args:
        input_path (str): 입력 이미지 경로
        output_dir (str): 출력 폴더 경로
        
    Returns:
        str: 복원된 이미지의 저장 경로
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'restored_imgs'), exist_ok=True)

    # 이미지 처리
    img_name = os.path.basename(input_path)
    basename = os.path.splitext(img_name)[0]
    input_img = cv2.imread(input_path, cv2.IMREAD_COLOR)

    # 이미지 복원
    _, _, restored_img = restorer.enhance(
        input_img,
        has_aligned=False,
        only_center_face=False,
        paste_back=True,
        weight=0.5)

    # 결과 저장
    save_restore_path = None
    if restored_img is not None:
        save_restore_path = os.path.join(output_dir, 'restored_imgs', f'{basename}.png')
        imwrite(restored_img, save_restore_path)
    
    return save_restore_path