# Script Execution Examples

All examples use the bundled `scripts/video.py`. For direct API calls via curl, see the Execution section in SKILL.md.

## Text-to-Video (t2v)

```bash
python3 scripts/video.py \
  --request '{"prompt":"A detective in a rainy city at night","size":"1280*720","duration":5}' \
  --print-response
```

### Multi-shot narrative

```bash
python3 scripts/video.py \
  --request '{"prompt":"第1个镜头[0-3秒] 雨夜街头侦探快步前行。第2个镜头[3-5秒] 侦探进入老旧建筑。","size":"1280*720","duration":5,"shot_type":"multi","prompt_extend":true}' \
  --model wan2.6-t2v --print-response
```

### With custom audio

```bash
python3 scripts/video.py \
  --request '{"prompt":"A cat general on a cliff","audio_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/bgm.mp3","size":"1280*720","duration":10}' \
  --model wan2.6-t2v --print-response
```

## Image-to-Video (i2v)

```bash
python3 scripts/video.py \
  --request '{"prompt":"A cat running on grass","img_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/frame.png","resolution":"720P","duration":5}' \
  --print-response
```

### With local file

```bash
python3 scripts/video.py \
  --request '{"prompt":"A cat running on grass","reference_image":"/path/to/image.png","resolution":"720P"}' \
  --print-response
```

## First + Last Frame (kf2v)

```bash
python3 scripts/video.py \
  --request '{"prompt":"A cat looks up to the sky","first_frame_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/first.png","last_frame_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/last.png","resolution":"720P"}' \
  --print-response
```

## Reference-based Video (r2v)

```bash
python3 scripts/video.py \
  --request '{"prompt":"character1 says hello to character2","reference_urls":["https://img.alicdn.com/imgextra/i1/NotRealJustExample/person.mp4","https://img.alicdn.com/imgextra/i1/NotRealJustExample/person2.png"],"size":"1280*720","duration":5,"shot_type":"multi"}' \
  --model wan2.6-r2v-flash --print-response
```

## VACE: Multi-Image Reference

```bash
python3 scripts/video.py \
  --request '{"function":"image_reference","prompt":"A girl walks through a forest","ref_images_url":["https://img.alicdn.com/imgextra/i1/NotRealJustExample/girl.png","https://img.alicdn.com/imgextra/i1/NotRealJustExample/forest.png"],"obj_or_bg":["obj","bg"],"size":"1280*720"}' \
  --model wan2.1-vace-plus --print-response
```

## VACE: Video Repainting

```bash
python3 scripts/video.py \
  --request '{"function":"video_repainting","prompt":"A steampunk car driving through a city","video_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/driving.mp4","control_condition":"depth","prompt_extend":false}' \
  --model wan2.1-vace-plus --print-response
```

## VACE: Video Local Edit

```bash
python3 scripts/video.py \
  --request '{"function":"video_edit","prompt":"A lion in a suit drinking coffee","video_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/cafe.mp4","mask_image_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/mask.png","mask_frame_id":1,"mask_type":"tracking","prompt_extend":false}' \
  --model wan2.1-vace-plus --print-response
```

## VACE: Video Extension

```bash
python3 scripts/video.py \
  --request '{"function":"video_extension","prompt":"A dog skateboarding, 3D cartoon","first_clip_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/clip.mp4","prompt_extend":false}' \
  --model wan2.1-vace-plus --print-response
```

## VACE: Video Outpainting

```bash
python3 scripts/video.py \
  --request '{"function":"video_outpainting","prompt":"A woman plays violin with an orchestra behind her","video_url":"https://img.alicdn.com/imgextra/i1/NotRealJustExample/violin.mp4","top_scale":1.5,"bottom_scale":1.5,"left_scale":1.5,"right_scale":1.5,"prompt_extend":false}' \
  --model wan2.1-vace-plus --print-response
```
