import os
import aiohttp
import pytesseract
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from src.backend.logger import get_logger
from src.backend.ingestion import log_to_dlq
import datetime
import unstructured
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.html import partition_html
from unstructured.partition.pptx import partition_pptx
from unstructured.partition.xlsx import partition_xlsx
from unstructured.partition.odt import partition_odt
from unstructured.partition.rtf import partition_rtf
from unstructured.partition.csv import partition_csv

load_dotenv()
logger = get_logger(__name__)
TESSERACT_LANGUAGES = os.getenv("TESSERACT_LANGUAGES", "eng")

async def process_attachments(attachment_urls: list) -> str:
    text = ""
    for url in attachment_urls:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download file: {url} (status {resp.status})")
                    content = await resp.read()
            filename = url.split("/")[-1].lower()
            if filename.endswith(".pdf"):
                try:
                    elements = partition_pdf(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"PDF parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".docx"):
                try:
                    elements = partition_docx(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"DOCX parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".txt"):
                try:
                    elements = partition_text(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"TXT parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".html"):
                try:
                    elements = partition_html(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"HTML parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".pptx"):
                try:
                    elements = partition_pptx(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"PPTX parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".xlsx"):
                try:
                    elements = partition_xlsx(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"XLSX parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".odt"):
                try:
                    elements = partition_odt(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"ODT parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".rtf"):
                try:
                    elements = partition_rtf(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"RTF parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(".csv"):
                try:
                    elements = partition_csv(file=BytesIO(content))
                    text += "\n".join([el.text for el in elements if hasattr(el, "text")])
                except Exception as e:
                    logger.warning(f"CSV parsing failed for {filename}: {e}")
                    raise
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')):
                try:
                    image = Image.open(BytesIO(content))
                    try:
                        ocr_text = pytesseract.image_to_string(image, lang=TESSERACT_LANGUAGES)
                        text += ocr_text
                    except pytesseract.TesseractError as e:
                        logger.warning(f"OCR failed for {filename}: {e}")
                        continue
                except Exception as e:
                    logger.warning(f"Image processing failed for {filename}: {e}")
                    continue
            else:
                logger.warning(f"Unsupported file type for {filename}")
                continue
        except Exception as e:
            logger.warning(f"Attachment processing failed for {url}: {e}")
            log_to_dlq({
                "original_request": {"attachment_url": url},
                "error_message": str(e),
                "failed_at_step": "attachment_processing",
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            continue
    return text 