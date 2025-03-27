import os
from datetime import datetime
import glob
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_pdf_report(output_filename="Stock_Market_Monitor.pdf"):
    """
    将所有生成的图表整合为一份完整的PDF报告
    
    参数:
    output_filename: 输出的PDF文件名
    """
    # 获取当前工作目录下的所有图片文件
    image_files = glob.glob('*.png')
    
    # 按生成的文件名排序
    def sort_key(filename):
        # 自定义排序函数
        if 'index_performance' in filename:
            return 1
        elif 'industry_moneyflow' in filename:
            return 2
        # 移除对行业个股的处理，原序号为3
        # elif 'industry_' in filename and 'stocks' in filename:
        #    return 3
        elif 'market_net_inflow' in filename:
            return 3
        # 移除对market_inflow_rate的处理
        # elif 'market_inflow_rate' in filename:
        #    return 4
        elif 'price_volume_divergence' in filename:
            return 4
        elif 'capital_concentration' in filename:
            return 5
        elif 'up_down_ratio' in filename:
            return 6
        else:
            return 100  # 其他文件放到最后
    
    # 排序图片文件
    image_files.sort(key=sort_key)
    
    # 打印找到的图片文件
    print(f"找到以下图片文件用于生成报告:")
    for img in image_files:
        print(f"- {img}")
    
    # 设置中文字体
    pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.ttf'))
    
    # 创建PDF文档
    doc = SimpleDocTemplate(output_filename, pagesize=A4)
    
    # 获取样式
    styles = getSampleStyleSheet()
    
    # 添加中文标题样式
    styles.add(ParagraphStyle(name='ChineseTitle',
                             fontName='SimHei',
                             fontSize=18,
                             leading=22,
                             alignment=1,  # 居中
                             spaceAfter=12))
    
    # 添加中文正文样式
    styles.add(ParagraphStyle(name='ChineseBody',
                             fontName='SimHei',
                             fontSize=10,
                             leading=14,
                             spaceAfter=6))
    
    # 添加中文小标题样式
    styles.add(ParagraphStyle(name='ChineseSubtitle',
                             fontName='SimHei',
                             fontSize=14,
                             leading=18,
                             spaceAfter=8))
    
    # 准备文档内容
    content = []
    
    # 添加报告标题
    title = Paragraph("股市监测系统日报", styles['ChineseTitle'])
    content.append(title)
    
    # 添加生成日期
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_paragraph = Paragraph(f"生成时间: {date_str}", styles['ChineseBody'])
    content.append(date_paragraph)
    content.append(Spacer(1, 0.5*cm))
    
    # 添加报告简介
    intro = Paragraph("本报告通过分析市场指数表现、行业资金流向、个股资金流向以及量价关系，"
                      "提供市场整体状况的多维度分析，帮助投资者了解市场热点和风险。", 
                      styles['ChineseBody'])
    content.append(intro)
    content.append(Spacer(1, 0.5*cm))
    
    # 添加目录标题
    toc_title = Paragraph("目录", styles['ChineseSubtitle'])
    content.append(toc_title)
    
    # 目录内容
    toc_data = [
        ["1.", "市场指数表现", "2"],
        ["2.", "行业资金流向", "3"],
        # 移除行业个股部分，并调整后续序号
        # ["3.", "热点行业个股资金流向", "4"],
        ["3.", "全市场个股资金净流入", "4"],
        ["4.", "量价背离指数", "5"],
        ["5.", "资金集中度指标", "6"],
        ["6.", "上涨/下跌股票比值", "7"]
    ]
    
    # 创建目录表格
    toc_table = Table(toc_data, colWidths=[0.7*cm, 10*cm, 0.7*cm])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEADING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    content.append(toc_table)
    content.append(Spacer(1, 1*cm))
    
    # 添加各部分内容
    section_num = 1
    
    # 依次添加每个部分的内容
    for img_file in image_files:
        if 'index_performance' in img_file:
            # 市场指数表现部分
            section_title = Paragraph(f"{section_num}. 市场指数表现", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分展示了主要市场指数的涨跌幅情况，包括上证指数、深证成指、沪深300等，"
                                  "帮助了解大盘整体走势和不同板块的表现差异。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
            
        elif 'industry_moneyflow' in img_file:
            # 行业资金流向部分
            section_title = Paragraph(f"{section_num}. 行业资金流向", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分分析各行业资金净流入/流出情况，按资金净流入额从高到低排序，"
                                  "帮助识别当日市场热门与冷门行业，把握行业轮动趋势。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
        
        # 注释掉热点行业个股资金流向部分
        """
        elif 'industry_' in img_file and 'stocks' in img_file:
            # 热点行业个股资金流向部分
            if section_num == 3:  # 只有第一个行业图片时添加标题和说明
                section_title = Paragraph(f"{section_num}. 热点行业个股资金流向", styles['ChineseSubtitle'])
                content.append(section_title)
                
                description = Paragraph("本部分深入分析了资金净流入最高的几个行业中各个股的资金流向情况，"
                                      "展示每个行业内部资金流入最高的个股，帮助发现行业龙头和热点个股。", styles['ChineseBody'])
                content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            # 只在所有行业图片添加完后增加section_num
            if 'industry_3_' in img_file or ('industry_2_' in img_file and not any('industry_3_' in f for f in image_files)):
                section_num += 1
                content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
        """
        
        if 'market_net_inflow' in img_file:
            # 全市场个股资金净流入部分
            section_title = Paragraph(f"{section_num}. 全市场个股资金净流入", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分分析了全市场资金净流入最高的股票，"
                                  "帮助发现市场大单关注的热点个股。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            # 移除资金净流入率图片的处理
            # 直接增加section_num
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
            
        elif 'price_volume_divergence' in img_file:
            # 量价背离指数部分
            section_title = Paragraph(f"{section_num}. 量价背离指数", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分计算了量价背离指数，即涨幅靠前但资金净流出的个股比例，"
                                  "以反映市场虚涨风险。当该指标超过30%时，市场可能面临回调风险。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
            
        elif 'capital_concentration' in img_file:
            # 资金集中度指标部分
            section_title = Paragraph(f"{section_num}. 资金集中度指标", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分计算了资金集中度指标，即市场前10%个股的资金净流入占全市场比例，"
                                  "反映市场资金分布情况。该指标越高，表明市场情绪越分化，热点越集中。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
            
        elif 'up_down_ratio' in img_file:
            # 上涨/下跌股票比值部分
            section_title = Paragraph(f"{section_num}. 上涨/下跌股票比值", styles['ChineseSubtitle'])
            content.append(section_title)
            
            description = Paragraph("本部分计算了市场上涨/下跌股票比值，即日内收盘上涨的股票数量与下跌股票数量的比值，"
                                  "反映市场整体强弱。比值大于1表示上涨家数多于下跌家数，市场整体偏强；"
                                  "比值小于1表示下跌家数多于上涨家数，市场整体偏弱；"
                                  "比值大于2或小于0.5通常表示市场处于明显的单边行情中。", styles['ChineseBody'])
            content.append(description)
            
            img = Image(img_file, width=16*cm, height=10*cm)
            content.append(img)
            content.append(Spacer(1, 0.5*cm))
            
            section_num += 1
            content.append(Paragraph("", styles['ChineseBody']))  # 添加分页符
    
    # 添加报告结论
    conclusion_title = Paragraph("报告结论", styles['ChineseSubtitle'])
    content.append(conclusion_title)
    
    conclusion = Paragraph("本报告通过多维度分析市场表现，为投资决策提供参考。请结合自身风险偏好和投资目标，"
                         "审慎使用本报告提供的信息。市场有风险，投资需谨慎。", styles['ChineseBody'])
    content.append(conclusion)
    
    # 构建并保存PDF
    doc.build(content)
    
    print(f"PDF报告已生成: {output_filename}")
    return output_filename

if __name__ == "__main__":
    create_pdf_report() 