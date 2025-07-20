import os
import requests
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import pandas as pd
import time

# 配置 Azure OpenAI API
API_KEY = 'f03dc7146838448a88e59f32363ab9b7'
ENDPOINT = "https://jcyopenai2.openai.azure.com/openai/deployments/jcy4o/chat/completions?api-version=2024-02-15-preview"

headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY,
}

# 根据合同类型定义提示词及对应字段
sales_contract_prompts = {
    "最终用户的公司名称": "Please provide only the final user's company name from this contract text.",
    "合同金额": "Please provide only the contract amount in yuan from this contract text.",
    "服务期限": "Please provide only the service term or contract expiration time from this contract text.",
    "买方的公司地址": "Please provide only the buyer's company address from this contract text.",
    "纳税人识别号": "Please provide only the taxpayer identification number from this contract text.",
    "银行信息": "Please provide only the bank account information from this contract text."
}

msp_agreement_prompts = {
    "服务时长": "Please provide only the duration of the service from this service agreement.",
    "服务期限": "Please provide only the validity period of the service from this service agreement."
}

# 初始化输出 DataFrame 的结构
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

# 通过 Azure API 使用 GPT-4o 获取每列内容的函数
def extract_content_with_azure(text, prompt):
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
    
    response = requests.post(ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
            
    response_json = response.json()
    if 'choices' in response_json and len(response_json['choices']) > 0:
        return clean_extracted_content(response_json['choices'][0]['message']['content'])

# 清理提取内容的函数
def clean_extracted_content(content):
    # 删除所有前导或尾随空格、换行符或不必要的文本
    cleaned_content = content.strip()
    return cleaned_content

# 将文本拆分成较小段的功能
def split_text(text, max_length=3000):
    """Splits text into chunks that are within the token limit."""
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []

    for paragraph in paragraphs:
        if sum(len(p) for p in current_chunk) + len(paragraph) <= max_length:
            current_chunk.append(paragraph)
        else:
            chunks.append("\n".join(current_chunk))
            current_chunk = [paragraph]

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

# 处理分段提取的函数
def extract_from_segments(text, prompts):
    """Extracts information from text divided into segments."""
    extracted_info = {key: "/" for key in prompts.keys()}
    
    # 将文本拆分成更小的块
    text_segments = split_text(text)
    
    for segment in text_segments:
        for key, prompt in prompts.items():
            # 仅在尚未填充时尝试提取
            if extracted_info[key] == "/":
                result = extract_content_with_azure(segment, prompt)
                if result.strip() != "/":
                    extracted_info[key] = result

    return extracted_info

# streamlit 布置
st.title("合同关键信息提取助手")
uploaded_file = st.file_uploader("请选择一个PDF文件", type="pdf")

if uploaded_file is not None:
    # 将上传的 PDF 转换为图像列表
    images = convert_from_bytes(uploaded_file.read())

    # 从每张图片（页面）中提取文本
    extracted_text = []
    for page_number, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang='chi_sim')  # 假设该文件的语言为中文
        extracted_text.append(text)

    # 将所有文本合并为一个字符串
    full_text = "\n".join(extracted_text)

    # 确定合同类型并提取相关信息
    if "买卖合同" in full_text or "服务合同" in full_text:
        st.write("检测到买卖合同或服务合同")
        extracted_info_sales = extract_from_segments(full_text, sales_contract_prompts)
        df = pd.DataFrame([extracted_info_sales])

    elif "MSP服务协议" in full_text:
        st.write("检测到MSP服务协议")
        extracted_info_msp = extract_from_segments(full_text, msp_agreement_prompts)
        df = pd.DataFrame([extracted_info_msp])

    else:
        st.warning("未能识别合同类型，请确认合同是否包含明确的标题。")

    # 可选择展示提取的文本
    #st.text(full_text)

    # 显示 DataFrame
    st.write(df)

    # 将DataFrame保存进csv
    csv_filename = "合同关键信息.csv"
    df.to_csv(csv_filename, index=False)

    # 提供下载csv的按钮
    with open(csv_filename, 'rb') as f:
        st.download_button(
            label="下载CSV文件",
            data=f,
            file_name=csv_filename,
            mime='text/csv'
        )
else:
    st.warning("请上传一个PDF文件。")

