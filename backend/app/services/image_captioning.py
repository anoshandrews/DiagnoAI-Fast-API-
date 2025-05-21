# import torch
# from PIL import Image
# from transformers import BlipProcessor, BlipForConditionalGeneration

# model_id = 'Salesforce/blip-image-captioning-base'
# model = BlipForConditionalGeneration.from_pretrained(model_id)
# processor = BlipProcessor.from_pretrained(model_id, use_fast=True)

# def run_inference(image_file):
#     image = Image.open(image_file).convert("RGB")
#     prompt = (
#         "Describe the condition shown in this image. "
#         "Does this look medically serious, or is it something that will heal on its own? "
#         "Should the person visit a doctor?"
#     )
#     inputs = processor(text=prompt, images=image, return_tensors="pt")
#     with torch.no_grad():
#         output = model.generate(**inputs, max_new_tokens=50)
#     return processor.decode(output[0], skip_special_tokens=True) 
