# donut_utils.py
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
from parser import parse_donut_output
from summarizer import summarize_invoice

MODEL_NAME = "naver-clova-ix/donut-base-finetuned-cord-v2"


def load_donut():
    processor = DonutProcessor.from_pretrained(MODEL_NAME)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return processor, model, device


def extract_with_donut(image: Image.Image, processor, model, device):
    """
    Run Donut on a PIL image and return parsed + summarized JSON.
    """
    task_prompt = "<s_cord-v2>"
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)

    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=model.config.decoder.max_position_embeddings,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
    )
    result = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    result = result.replace(task_prompt, "").strip()
    parsed = parse_donut_output(result)
    summary = summarize_invoice(parsed)
    return {"structured_data": summary, "raw_parsed": parsed}
