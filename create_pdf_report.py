import os
from datetime import datetime
import glob
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor

def create_pdf_report(output_filename="Stock_Market_Monitor.pdf"):
    """
    创建PDF报告，将当前目录下的行业资金流向和个股资金流向图片整合到一个PDF文件中
    
    参数:
    output_filename: 输出的PDF文件名，默认为'Stock_Market_Monitor.pdf'
    """
    print(f"开始创建PDF报告: {output_filename}")
    
    # 查找所有相关图片
    industry_moneyflow_images = glob.glob('industry_moneyflow_top_bottom_*.png')  # 行业资金流向图片
    industry_stocks_images = glob.glob('industry_*_stocks_*.png')  # 个股资金流向图片
    index_performance_images = glob.glob('index_performance_*.png')  # 指数表现图片
    # 移除已经包含在industry_moneyflow_images中的图片
    industry_stocks_images = [img for img in industry_stocks_images if img not in industry_moneyflow_images]
    
    # 按日期排序（假设文件名中包含日期信息，格式为YYYYMMDD）
    def extract_date(filename):
        # 尝试从文件名中提取日期
        parts = filename.split('_')
        for part in parts:
            if len(part) == 8 and part.isdigit():
                return part
        return "00000000"  # 默认日期，确保文件不会因为没有日期而被排除
    
    # 对图片按日期排序
    industry_moneyflow_images.sort(key=extract_date, reverse=True)
    industry_stocks_images.sort(key=extract_date, reverse=True)
    index_performance_images.sort(key=extract_date, reverse=True)
    
    # 检查是否找到图片
    all_images = index_performance_images + industry_moneyflow_images + industry_stocks_images
    if not all_images:
        print("未找到任何图片文件，无法创建PDF报告")
        return
    
    print(f"找到 {len(all_images)} 个图片文件:")
    print(f"  - 指数表现图片: {len(index_performance_images)} 个")
    print(f"  - 行业资金流向图片: {len(industry_moneyflow_images)} 个")
    print(f"  - 个股资金流向图片: {len(industry_stocks_images)} 个")
    
    for img in all_images:
        print(f"  - {img}")
    
    # 创建PDF文档
    c = canvas.Canvas(output_filename, pagesize=landscape(A4))
    width, height = landscape(A4)  # A4纸横向尺寸
    
    # 注册中文字体（如果需要）
    try:
        # 尝试注册微软雅黑字体
        pdfmetrics.registerFont(TTFont('MSYaHei', 'msyh.ttf'))
        cn_font = 'MSYaHei'
    except:
        try:
            # 尝试注册宋体
            pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))
            cn_font = 'SimSun'
        except:
            # 如果都失败，使用默认字体
            cn_font = 'Helvetica'
            print("警告：未能加载中文字体，可能导致中文显示问题")
    
    # 添加封面
    c.setFillColor(HexColor('#0066CC'))
    c.rect(0, 0, width, height, fill=True)
    
    # 添加标题
    c.setFont(cn_font, 36)
    c.setFillColor(HexColor('#FFFFFF'))
    title = "Stock Market Monitor"
    title_width = stringWidth(title, cn_font, 36)
    c.drawString((width - title_width) / 2, height - 150, title)
    
    # 添加副标题
    c.setFont(cn_font, 24)
    subtitle = "行业与个股资金流向分析报告"
    subtitle_width = stringWidth(subtitle, cn_font, 24)
    c.drawString((width - subtitle_width) / 2, height - 200, subtitle)
    
    # 添加日期
    today = datetime.now().strftime('%Y-%m-%d')
    c.setFont(cn_font, 18)
    date_str = f"生成日期: {today}"
    date_width = stringWidth(date_str, cn_font, 18)
    c.drawString((width - date_width) / 2, height - 250, date_str)
    
    # 添加页脚
    c.setFont(cn_font, 10)
    footer = "由Tushare数据API提供技术支持"
    footer_width = stringWidth(footer, cn_font, 10)
    c.drawString((width - footer_width) / 2, 30, footer)
    
    c.showPage()  # 结束当前页面
    
    # 添加目录页
    total_images = len(all_images)
    page_count = total_images + 2  # 封面+目录+图像页数
    
    c.setFont(cn_font, 24)
    c.setFillColor(HexColor('#000000'))
    c.drawString(30, height - 50, "目录")
    
    c.setFont(cn_font, 12)
    line_height = 20
    current_y = height - 100
    
    # 添加指数表现部分到目录
    if index_performance_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "一、市场指数表现")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        for i, img_path in enumerate(index_performance_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 绘制目录项
            index_text = f"1.{i+1} 市场指数表现 ({formatted_date})"
            c.drawString(70, current_y, index_text)
            
            # 绘制页码和点线
            page_num = i + 3  # 封面(1) + 目录(1) + 当前索引
            c.drawString(width - 100, current_y, str(page_num))
            
            # 在文本和页码之间添加点线
            dots_width = width - 200 - stringWidth(index_text, cn_font, 12)
            c.setDash([1, 2], 0)
            c.line(70 + stringWidth(index_text, cn_font, 12) + 10, 
                   current_y + 4, width - 110, current_y + 4)
            
            current_y -= line_height
            
            # 如果页面空间不足，创建新页
            if current_y < 50:
                c.showPage()
                c.setFont(cn_font, 24)
                c.drawString(30, height - 50, "目录(续)")
                c.setFont(cn_font, 12)
                current_y = height - 100
    
    # 添加行业资金流向部分到目录
    if industry_moneyflow_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "二、行业资金流向")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        start_page = len(index_performance_images) + 3  # 封面(1) + 目录(1) + 指数页数
        
        for i, img_path in enumerate(industry_moneyflow_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 绘制目录项
            index_text = f"2.{i+1} 行业资金流向分析 ({formatted_date})"
            c.drawString(70, current_y, index_text)
            
            # 绘制页码和点线
            page_num = start_page + i
            c.drawString(width - 100, current_y, str(page_num))
            
            # 在文本和页码之间添加点线
            c.setDash([1, 2], 0)
            c.line(70 + stringWidth(index_text, cn_font, 12) + 10, 
                   current_y + 4, width - 110, current_y + 4)
            
            current_y -= line_height
            
            # 如果页面空间不足，创建新页
            if current_y < 50:
                c.showPage()
                c.setFont(cn_font, 24)
                c.drawString(30, height - 50, "目录(续)")
                c.setFont(cn_font, 12)
                current_y = height - 100
    
    # 添加个股资金流向部分到目录
    if industry_stocks_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "三、个股资金流向")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        start_page = len(index_performance_images) + len(industry_moneyflow_images) + 3  # 封面(1) + 目录(1) + 指数页数 + 行业页数
        
        for i, img_path in enumerate(industry_stocks_images):
            # 尝试从文件名中提取行业名称
            filename_parts = os.path.basename(img_path).split('_')
            industry_name = "未知行业"
            if len(filename_parts) > 2:
                industry_name = filename_parts[1]
            
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 绘制目录项
            index_text = f"3.{i+1} {industry_name}行业个股资金流向 ({formatted_date})"
            c.drawString(70, current_y, index_text)
            
            # 绘制页码和点线
            page_num = start_page + i
            c.drawString(width - 100, current_y, str(page_num))
            
            # 在文本和页码之间添加点线
            c.setDash([1, 2], 0)
            c.line(70 + stringWidth(index_text, cn_font, 12) + 10, 
                   current_y + 4, width - 110, current_y + 4)
            
            current_y -= line_height
            
            # 如果页面空间不足，创建新页
            if current_y < 50:
                c.showPage()
                c.setFont(cn_font, 24)
                c.drawString(30, height - 50, "目录(续)")
                c.setFont(cn_font, 12)
                current_y = height - 100
    
    c.showPage()  # 结束目录页
    
    # 添加指数表现图片
    for i, img_path in enumerate(index_performance_images):
        try:
            # 提取日期
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 添加页眉
            c.setFont(cn_font, 16)
            c.setFillColor(HexColor('#000000'))
            header = f"市场指数表现 ({formatted_date})"
            c.drawString(30, height - 30, header)
            
            # 加载图片
            img = ImageReader(img_path)
            img_width, img_height = img.getSize()
            
            # 计算图片显示尺寸，保持比例
            display_width = width - 60  # 左右各留30的边距
            scale = display_width / img_width
            display_height = img_height * scale
            
            # 确保图片高度不超过页面
            if display_height > height - 100:  # 上下各留50的边距
                display_height = height - 100
                scale = display_height / img_height
                display_width = img_width * scale
            
            # 在页面中央绘制图片
            x = (width - display_width) / 2
            y = (height - display_height) / 2
            c.drawImage(img, x, y, width=display_width, height=display_height)
            
            # 添加页脚
            c.setFont(cn_font, 10)
            c.drawString(30, 30, f"第 {i+3} 页")  # 封面(1) + 目录(1) + 当前页码
            c.drawString(width - 150, 30, "Stock Market Monitor")
            
            c.showPage()  # 结束当前页面
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")
    
    # 添加行业资金流向图片
    start_page = len(index_performance_images) + 3  # 封面(1) + 目录(1) + 指数页数
    for i, img_path in enumerate(industry_moneyflow_images):
        try:
            # 提取日期
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 添加页眉
            c.setFont(cn_font, 16)
            c.setFillColor(HexColor('#000000'))
            header = f"行业资金流向分析 ({formatted_date})"
            c.drawString(30, height - 30, header)
            
            # 加载图片
            img = ImageReader(img_path)
            img_width, img_height = img.getSize()
            
            # 计算图片显示尺寸，保持比例
            display_width = width - 60  # 左右各留30的边距
            scale = display_width / img_width
            display_height = img_height * scale
            
            # 确保图片高度不超过页面
            if display_height > height - 100:  # 上下各留50的边距
                display_height = height - 100
                scale = display_height / img_height
                display_width = img_width * scale
            
            # 在页面中央绘制图片
            x = (width - display_width) / 2
            y = (height - display_height) / 2
            c.drawImage(img, x, y, width=display_width, height=display_height)
            
            # 添加页脚
            c.setFont(cn_font, 10)
            page_num = start_page + i
            c.drawString(30, 30, f"第 {page_num} 页")
            c.drawString(width - 150, 30, "Stock Market Monitor")
            
            c.showPage()  # 结束当前页面
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")
    
    # 添加个股资金流向图片
    start_page = len(index_performance_images) + len(industry_moneyflow_images) + 3  # 封面(1) + 目录(1) + 指数页数 + 行业页数
    for i, img_path in enumerate(industry_stocks_images):
        try:
            # 提取日期和行业名称
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 尝试从文件名中提取行业名称
            filename_parts = os.path.basename(img_path).split('_')
            industry_name = "未知行业"
            if len(filename_parts) > 2:
                industry_name = filename_parts[1]
            
            # 添加页眉
            c.setFont(cn_font, 16)
            c.setFillColor(HexColor('#000000'))
            header = f"{industry_name}行业个股资金流向 ({formatted_date})"
            c.drawString(30, height - 30, header)
            
            # 加载图片
            img = ImageReader(img_path)
            img_width, img_height = img.getSize()
            
            # 计算图片显示尺寸，保持比例
            display_width = width - 60  # 左右各留30的边距
            scale = display_width / img_width
            display_height = img_height * scale
            
            # 确保图片高度不超过页面
            if display_height > height - 100:  # 上下各留50的边距
                display_height = height - 100
                scale = display_height / img_height
                display_width = img_width * scale
            
            # 在页面中央绘制图片
            x = (width - display_width) / 2
            y = (height - display_height) / 2
            c.drawImage(img, x, y, width=display_width, height=display_height)
            
            # 添加页脚
            c.setFont(cn_font, 10)
            page_num = start_page + i
            c.drawString(30, 30, f"第 {page_num} 页")
            c.drawString(width - 150, 30, "Stock Market Monitor")
            
            c.showPage()  # 结束当前页面
        except Exception as e:
            print(f"处理图片 {img_path} 时出错: {e}")
    
    # 保存PDF文件
    c.save()
    print(f"PDF报告已成功创建: {output_filename}")
    print(f"报告包含 {len(all_images)} 张图片，共 {page_count} 页")

if __name__ == "__main__":
    create_pdf_report() 