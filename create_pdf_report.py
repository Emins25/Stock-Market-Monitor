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
    market_moneyflow_images = glob.glob('market_net_inflow_top_*.png') + glob.glob('market_inflow_rate_top_*.png')  # 市场资金流向图片
    divergence_images = glob.glob('price_volume_divergence_index_*.png')  # 量价背离指数图片
    concentration_images = glob.glob('capital_concentration_index_*.png')  # 资金集中度指标图片
    
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
    market_moneyflow_images.sort(key=extract_date, reverse=True)
    divergence_images.sort(key=extract_date, reverse=True)
    concentration_images.sort(key=extract_date, reverse=True)
    
    # 检查是否找到图片
    all_images = (index_performance_images + industry_moneyflow_images + industry_stocks_images + 
                 market_moneyflow_images + divergence_images + concentration_images)
    if not all_images:
        print("未找到任何图片文件，无法创建PDF报告")
        return
    
    print(f"找到 {len(all_images)} 个图片文件:")
    print(f"  - 指数表现图片: {len(index_performance_images)} 个")
    print(f"  - 行业资金流向图片: {len(industry_moneyflow_images)} 个")
    print(f"  - 个股资金流向图片: {len(industry_stocks_images)} 个")
    print(f"  - 市场资金流向图片: {len(market_moneyflow_images)} 个")
    print(f"  - 量价背离指数图片: {len(divergence_images)} 个")
    print(f"  - 资金集中度指标图片: {len(concentration_images)} 个")
    
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
    subtitle = "市场监测系统分析报告"
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
        start_page = len(index_performance_images) + len(industry_moneyflow_images) + 3  # 封面(1) + 目录(1) + 前面的图片页数
        
        for i, img_path in enumerate(industry_stocks_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 提取行业名称
            industry_name = img_path.split('_')[1] if len(img_path.split('_')) > 1 else "未知行业"
            
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
    
    # 添加市场资金流向部分到目录
    if market_moneyflow_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "四、市场资金流向")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        start_page = (len(index_performance_images) + len(industry_moneyflow_images) + 
                     len(industry_stocks_images) + 3)  # 封面(1) + 目录(1) + 前面的图片页数
        
        for i, img_path in enumerate(market_moneyflow_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 判断是净流入榜还是流入率榜
            if 'rate' in img_path:
                title = "个股资金流入率排行"
            else:
                title = "个股资金净流入排行"
            
            # 绘制目录项
            index_text = f"4.{i+1} {title} ({formatted_date})"
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
    
    # 添加量价背离指数部分到目录
    if divergence_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "五、量价背离指数")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        start_page = (len(index_performance_images) + len(industry_moneyflow_images) + 
                     len(industry_stocks_images) + len(market_moneyflow_images) + 3)
        
        for i, img_path in enumerate(divergence_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 绘制目录项
            index_text = f"5.{i+1} 量价背离指数分析 ({formatted_date})"
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
    
    # 添加资金集中度指标部分到目录
    if concentration_images:
        c.setFont(cn_font, 16)
        c.drawString(50, current_y, "六、资金集中度指标")
        current_y -= line_height * 1.5
        
        c.setFont(cn_font, 12)
        start_page = (len(index_performance_images) + len(industry_moneyflow_images) + 
                     len(industry_stocks_images) + len(market_moneyflow_images) + 
                     len(divergence_images) + 3)
        
        for i, img_path in enumerate(concentration_images):
            img_date = extract_date(img_path)
            if len(img_date) == 8:
                formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
            else:
                formatted_date = "未知日期"
            
            # 绘制目录项
            index_text = f"6.{i+1} 资金集中度指标分析 ({formatted_date})"
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
    
    # 函数：添加图片到PDF页面
    def add_image_to_page(image_path, title=None):
        try:
            # 读取图片
            img = ImageReader(image_path)
            
            # 获取图片宽高比
            img_width, img_height = img.getSize()
            aspect = img_width / float(img_height)
            
            # 计算图片在页面上的尺寸和位置
            max_width = width - 50
            max_height = height - 100
            
            if aspect > max_width / max_height:  # 宽度受限
                display_width = max_width
                display_height = display_width / aspect
            else:  # 高度受限
                display_height = max_height
                display_width = display_height * aspect
            
            # 添加标题
            if title:
                c.setFont(cn_font, 14)
                title_width = stringWidth(title, cn_font, 14)
                c.drawString((width - title_width) / 2, height - 30, title)
            
            # 计算图片位置（居中）
            x_pos = (width - display_width) / 2
            y_pos = (height - display_height) / 2
            
            # 绘制图片
            c.drawImage(img, x_pos, y_pos, width=display_width, height=display_height)
            
            # 添加页脚
            c.setFont(cn_font, 8)
            c.drawString(30, 20, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d')}")
            
            c.showPage()
            
            return True
        except Exception as e:
            print(f"添加图片 {image_path} 时出错: {e}")
            return False
    
    # 添加指数表现图片
    for img_path in index_performance_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        title = f"市场指数表现 ({formatted_date})"
        add_image_to_page(img_path, title)
    
    # 添加行业资金流向图片
    for img_path in industry_moneyflow_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        title = f"行业资金流向分析 ({formatted_date})"
        add_image_to_page(img_path, title)
    
    # 添加个股资金流向图片
    for img_path in industry_stocks_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        # 提取行业名称
        industry_name = img_path.split('_')[1] if len(img_path.split('_')) > 1 else "未知行业"
        
        title = f"{industry_name}行业个股资金流向 ({formatted_date})"
        add_image_to_page(img_path, title)
    
    # 添加市场资金流向图片
    for img_path in market_moneyflow_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        # 判断是净流入榜还是流入率榜
        if 'rate' in img_path:
            title = f"个股资金流入率排行 ({formatted_date})"
        else:
            title = f"个股资金净流入排行 ({formatted_date})"
        
        add_image_to_page(img_path, title)
    
    # 添加量价背离指数图片
    for img_path in divergence_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        title = f"量价背离指数分析 ({formatted_date})"
        add_image_to_page(img_path, title)
    
    # 添加资金集中度指标图片
    for img_path in concentration_images:
        img_date = extract_date(img_path)
        if len(img_date) == 8:
            formatted_date = f"{img_date[:4]}-{img_date[4:6]}-{img_date[6:]}"
        else:
            formatted_date = "未知日期"
        
        title = f"资金集中度指标分析 ({formatted_date})"
        add_image_to_page(img_path, title)
    
    # 保存PDF文件
    c.save()
    print(f"PDF报告已成功生成: {output_filename}")
    
    return output_filename

if __name__ == "__main__":
    create_pdf_report() 