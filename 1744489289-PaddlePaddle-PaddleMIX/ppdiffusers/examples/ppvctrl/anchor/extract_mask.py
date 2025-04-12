import argparse
import os
import sys
from moviepy.editor import ImageSequenceClip
import cv2
import numpy as np
import paddle
import paddle.nn.functional as F
import supervision as sv
from PIL import Image

current_dir = os.getcwd()
paddlemix_dir = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.append(os.path.join(paddlemix_dir,'paddlemix/models'))
sys.path.append(os.path.join(os.getcwd(), "paddlemix/models"))

from paddlemix.models.groundingdino.modeling import GroundingDinoModel
from paddlemix.processors.groundingdino_processing import GroundingDinoProcessor
from utils.video_utils import create_video,save_video_from_bgr
from paddlemix.models.sam2.build_sam import build_sam2, build_sam2_video_predictor
from paddlemix.models.sam2.sam2_image_predictor import SAM2ImagePredictor

if __name__=='__main__': 
    # parser = argparse.ArgumentParser("Grounded-Segment-Anything Demo", add_help=True)
    # args = parser.parse_args()
    
    # args.dino_model_name_or_path = "GroundingDino/groundingdino-swint-ogc"
    # args.input_path='/root/paddlejob/workspace/env_run/output/haoming/fork/PaddleMIX/ppdiffusers/examples/ppvctrl/infer_outputs/mask2video/i2v/output.mp4'
    # args.prompt="A dark gray Mini Cooper "
    # args.box_threshold=0.6
    # args.text_threshold=0.25
    # args.output_path="output.mp4"
    
    # sam2_checkpoint="/root/paddlejob/workspace/env_run/output/haoming/fork/PaddleMIX/ppdiffusers/examples/ppvctrl/anchor/sam2.1_hiera_large.pdparams"
    # model_cfg="configs/sam2.1_hiera_l.yaml"
    parser = argparse.ArgumentParser("Grounded-Segment-Anything Demo", add_help=True)
    parser.add_argument(
        "--dino_model_name_or_path",
        type=str,
        default="GroundingDino/groundingdino-swint-ogc",
        help="Path to pretrained model or model identifier",
    )
    parser.add_argument(
        "--sam2_config", 
        type=str,
        default="configs/sam2.1_hiera_l.yaml", 
        help="path to config file")

    parser.add_argument(
        "--sam2_checkpoint", 
        type=str, 
        default="anchor/checkpoints/mask/sam2.1_hiera_large.pdparams",
        help="path to sam checkpoint file")

    parser.add_argument("--input_path", type=str, default=None)
    parser.add_argument("--control_video_path", type=str, default="guide_values.mp4")
    parser.add_argument("--mask_video_path", type=str, default="mask_values.mp4")
    parser.add_argument("--reference_image_path", type=str, default="reference_image.jpg")
    
    parser.add_argument("--prompt", type=str, required=True, help="The prompt of the vidoe to be segmented.")
    parser.add_argument("--box_threshold", type=float, default=0.6)
    parser.add_argument("--text_threshold", type=float, default=0.25)
    
    args = parser.parse_args()
    
    model_cfg=args.sam2_config
    sam2_checkpoint=args.sam2_checkpoint
    processor = GroundingDinoProcessor.from_pretrained(args.dino_model_name_or_path)
    dino_model = GroundingDinoModel.from_pretrained(args.dino_model_name_or_path)
    dino_model.eval()
    
    video_predictor = build_sam2_video_predictor(model_cfg, sam2_checkpoint)
    sam2_image_model = build_sam2(model_cfg, sam2_checkpoint)
    image_predictor = SAM2ImagePredictor(sam2_image_model)
    
    inference_state = video_predictor.init_state(video_path=args.input_path)
    org_frames = inference_state["org_frames"]
    fps = inference_state["fps"]
    ann_frame_idx = 0

    image_pil = Image.fromarray(org_frames[0]).convert("RGB")
    print(len(org_frames),org_frames[0].shape)
    
    W, H = image_pil.size
    image_tensor, mask, tokenized_out = processor(images=image_pil, text=args.prompt)

    
    with paddle.no_grad():
        outputs = dino_model(
            image_tensor,
            mask,
            input_ids=tokenized_out["input_ids"],
            attention_mask=tokenized_out["attention_mask"],
            text_self_attention_masks=tokenized_out["text_self_attention_masks"],
            position_ids=tokenized_out["position_ids"],
        )

    logits = F.sigmoid(outputs["pred_logits"])[0]  # (nq, 256)
    boxes = outputs["pred_boxes"][0]  # (nq, 4)
    
    logits_filt = logits.clone()
    boxes_filt = boxes.clone()
    filt_mask = logits_filt.max(axis=1) > args.box_threshold #nq

    logits_filt = logits_filt[filt_mask]  # num_filt
    boxes_filt = boxes_filt[filt_mask]  # num_filt

    # build pred
    pred_phrases = []
    pred_boxes = []
    for logit, box in zip(logits_filt, boxes_filt):
        pred_phrase = processor.decode(logit > args.text_threshold)
        pred_phrases.append(pred_phrase)

        box = box * paddle.to_tensor([W, H, W, H]).astype(paddle.float32)
        # from xywh to xyxy
        box[:2] -= box[2:] / 2
        box[2:] += box[:2]

        pred_boxes.append(box)

    input_boxes = np.array(pred_boxes)
    OBJECTS = pred_phrases

    for object_id, (label, box) in enumerate(zip(OBJECTS, input_boxes), start=1):
        _, out_obj_ids, out_mask_logits = video_predictor.add_new_points_or_box(
            inference_state=inference_state,
            frame_idx=ann_frame_idx,
            obj_id=object_id,
            box=box,
        )

    video_segments = {}
    for out_frame_idx, out_obj_ids, out_mask_logits in video_predictor.propagate_in_video(inference_state):
        video_segments[out_frame_idx] = {
            out_obj_id: (out_mask_logits[i] > 0.0).cpu().numpy() for i, out_obj_id in enumerate(out_obj_ids)
        }

    ID_TO_OBJECTS = {i: obj for i, obj in enumerate(OBJECTS, start=1)}
 
    reference_img=cv2.cvtColor(org_frames[0], cv2.COLOR_BGR2RGB)
    annotated_frames = []
    mask_=[]
    for frame_idx, segments in video_segments.items():
        if frame_idx==0:
            first_frame=org_frames[frame_idx]
            first_mask = list(segments.values())
            first_mask = np.concatenate(first_mask, axis=0)[0]
            rgb_frame_0=np.zeros((480, 720, 3), dtype=np.uint8)
            rgb_frame_0[first_mask]=1
            cv2.imwrite(args.reference_image_path.replace("reference","control"),rgb_frame_0*255)

        
        img=org_frames[frame_idx]
        object_ids = list(segments.keys())
        masks = list(segments.values())
        masks = np.concatenate(masks, axis=0)[0]
        img[masks]=0
        rgb_frame = np.ones((480, 720, 3), dtype=np.uint8)
        rgb_frame=rgb_frame*255
        rgb_frame[masks] = 0
        annotated_frames.append(img)
        mask_.append(rgb_frame)
        
        # detections = sv.Detections(
        #     xyxy=sv.mask_to_xyxy(masks), mask=masks, class_id=np.array(object_ids, dtype=np.int32)
        # )
        # mask_annotator = sv.MaskAnnotator()
        # annotated_frame = mask_annotator.annotate(scene=img.copy(), detections=detections)
        # annotated_frames.append(annotated_frame)
       


    save_video_from_bgr(annotated_frames, args.control_video_path, frame_rate=30, width=W, height=H)
    save_video_from_bgr(mask_, args.mask_video_path, frame_rate=30, width=W, height=H)
    
    cv2.imwrite(args.reference_image_path,reference_img)