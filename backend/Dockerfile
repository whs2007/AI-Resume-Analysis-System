# 阿里云函数计算 FC 自定义容器镜像
FROM python:3.11-slim

WORKDIR /code

# 安装系统依赖（PyMuPDF 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# FC 自定义运行时通过 HTTP 协议与函数通信
EXPOSE 9000

# 启动 uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
