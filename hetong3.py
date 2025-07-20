import os
import requests
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import pandas as pd
import time

# Configuration for Azure OpenAI API
API_KEY = 'f03dc7146838448a88e59f32363ab9b7'
ENDPOINT = "https://jcyopenai2.openai.azure.com/openai/deployments/jcy4o/chat/completions?api-version=2024-02-15-preview"

headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY,
}

# Define prompt words and corresponding fields based on contract type
sales_contract_prompts = {
    "最终用户的公司名称": "Please extract the final user's company name from this contract text.",
    "合同金额": "Please extract the contract amount in yuan from this contract text.",
    "服务期限": "Please extract the service term or validy period or contract expiration time from this contract text.",
    "买方的公司地址": "Please extract the buyer's company address from this contract text.",
    "纳税人识别号": "Please extract the taxpayer identification number from this contract text.",
    "银行信息": "Please extract the bank account from this contract text."
}

msp_agreement_prompts = {
    "服务时长": "Please extract the duration of the service from this service agreement.",
    "服务期限": "Please extract the validity period of the service from this service agreement."
}

# Initialize the structure of the output DataFrame
columns_for_sales = [
    "最终用户的公司名称",
    "合同金额",
    "服务期限",
    "买方的公司地址",
    "纳税人识别号",
    "银行信息"
]
columns_for_msp = [
    "服务时长",
    "服务期限"
]

extracted_info_sales = {col: "/" for col in columns_for_sales}
extracted_info_msp = {col: "/" for col in columns_for_msp}

# Function to get content for each column using GPT-4 via Azure API
def extract_content_with_azure(text, prompt, retry_attempts=5):
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "你是一个北京信诺时代科技发展有限公司的合同关键信息提取助手，用户将询问有关签约客户的合同关键信息，你需要在与不同客户签署的买卖合同和MSP服务协议中，提取出如下的关键信息。"
            },
            {
                "role": "user",
                "content": f"{prompt}\n\n{text}"
            }
        ],
        "temperature": 0.5,
        "top_p": 0.95,
        "max_tokens": 150
    }
    
    for attempt in range(retry_attempts):
        try:
            response = requests.post(ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            
            response_json = response.json()
            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content']
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit error
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                st.error(f"Request failed: {e}")
                return "/"
        
    st.error("Exceeded retry attempts. Please try again later.")
    return "/"

# Streamlit application setup
st.title("合同关键信息提取助手")

# File uploader
uploaded_file = st.file_uploader("请选择一个PDF文件", type="pdf")

if uploaded_file is not None:
    # Convert the uploaded PDF to a list of images
    images = convert_from_bytes(uploaded_file.read())

    # Extract text from each image (page)
    extracted_text = []
    for page_number, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang='chi_sim')  # assuming the document is in Chinese
        extracted_text.append(text)

    # Combine all text into a single string
    full_text = "\n".join(extracted_text)

    # Determine contract type and extract relevant information
    if "买卖合同" in full_text or "服务合同" in full_text:
        st.write("检测到买卖合同或服务合同")
        for key, prompt in sales_contract_prompts.items():
            extracted_info_sales[key] = extract_content_with_azure(full_text, prompt)
        df = pd.DataFrame([extracted_info_sales])

    elif "MSP服务协议" in full_text:
        st.write("检测到MSP服务协议")
        for key, prompt in msp_agreement_prompts.items():
            extracted_info_msp[key] = extract_content_with_azure(full_text, prompt)
        df = pd.DataFrame([extracted_info_msp])

    else:
        st.warning("未能识别合同类型，请确认合同是否包含明确的标题。")

    st.text(full_text)

    # Display the DataFrame in the app
    st.write(df)

    # Save the DataFrame to a CSV file
    csv_filename = "extracted_contract_info.csv"
    df.to_csv(csv_filename, index=False)

    # Provide a download link for the CSV file
    st.markdown(f"[下载CSV文件](./{csv_filename})")
else:
    st.warning("请上传一个PDF文件。")