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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import platform

def create_pdf_report(output_filename="Stock_Market_Monitor.pdf"):
    """
    创建市场监测PDF报告
    
    参数:
        output_filename: 输出的PDF文件名
    """
    # 注册字体
    # 根据不同操作系统选择合适的字体
    system = platform.system()
    
    # 注册中文楷体字体
    chinese_font_registered = False
    english_font_registered = False
    
    if system == 'Windows':
        # Windows系统使用楷体和Times New Roman
        try:
            # 尝试楷体
            pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/simkai.ttf'))
            print("已注册字体: 楷体")
            chinese_font_registered = True
        except:
            try:
                # 如果没有楷体，尝试使用微软雅黑
                pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/msyh.ttc'))
                print("已注册字体: 微软雅黑")
                chinese_font_registered = True
            except Exception as e:
                try:
                    # 再尝试宋体
                    pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/simsun.ttc'))
                    print("已注册字体: 宋体")
                    chinese_font_registered = True
                except Exception as e:
                    print(f"注册中文字体失败: {e}")
                    print("将使用默认字体，可能导致中文显示为乱码")
        
        try:
            # 注册Times New Roman英文字体
            pdfmetrics.registerFont(TTFont('english_font', 'C:/Windows/Fonts/times.ttf'))
            print("已注册字体: Times New Roman")
            english_font_registered = True
        except Exception as e:
            print(f"注册英文字体失败: {e}")
            print("将使用默认字体")
    
    elif system == 'Darwin':  # macOS
        try:
            # macOS系统使用楷体或华文黑体
            pdfmetrics.registerFont(TTFont('chinese_font', '/System/Library/Fonts/STKaiti.ttc'))
            print("已注册字体: 楷体")
            chinese_font_registered = True
        except:
            try:
                pdfmetrics.registerFont(TTFont('chinese_font', '/System/Library/Fonts/PingFang.ttc'))
                print("已注册字体: 苹方")
                chinese_font_registered = True
            except Exception as e:
                print(f"注册中文字体失败: {e}")
        
        try:
            # 注册Times New Roman英文字体
            pdfmetrics.registerFont(TTFont('english_font', '/Library/Fonts/Times New Roman.ttf'))
            print("已注册字体: Times New Roman")
            english_font_registered = True
        except Exception as e:
            print(f"注册英文字体失败: {e}")
    
    else:  # Linux或其他系统
        try:
            # Linux系统尝试使用楷体或文泉驿
            pdfmetrics.registerFont(TTFont('chinese_font', '/usr/share/fonts/chinese/simkai.ttf'))
            print("已注册字体: 楷体")
            chinese_font_registered = True
        except:
            try:
                pdfmetrics.registerFont(TTFont('chinese_font', '/usr/share/fonts/wenquanyi/wqy-microhei.ttc'))
                print("已注册字体: 文泉驿微米黑")
                chinese_font_registered = True
            except Exception as e:
                print(f"注册中文字体失败: {e}")
        
        try:
            # 注册Times New Roman英文字体
            pdfmetrics.registerFont(TTFont('english_font', '/usr/share/fonts/TTF/times.ttf'))
            print("已注册字体: Times New Roman")
            english_font_registered = True
        except Exception as e:
            print(f"注册英文字体失败: {e}")
    
    # 如果没有成功注册字体，使用默认字体
    if not chinese_font_registered:
        chinese_font = 'Helvetica'
    else:
        chinese_font = 'chinese_font'
    
    if not english_font_registered:
        english_font = 'Helvetica'
    else:
        english_font = 'english_font'
    
    # 获取最近生成的图表文件
    def get_latest_figure(pattern):
        files = glob.glob(pattern)
        if not files:
            return None
        # 按修改时间排序，获取最新的文件
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    
    # 创建文档
    doc = SimpleDocTemplate(output_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 创建自定义样式，使用已注册的字体
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=24,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=16,
        textColor=colors.darkblue,
        spaceBefore=10,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10,
        spaceBefore=5,
        spaceAfter=5
    )
    
    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=9,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceBefore=5,
        spaceAfter=15
    )
    
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=9,
        textColor=colors.black,
        alignment=TA_JUSTIFY,
        spaceBefore=5,
        spaceAfter=10,
        leftIndent=20,
        rightIndent=20
    )
    
    # 获取今天的日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 准备内容
    content = []
    
    # 标题
    content.append(Paragraph(f"股票市场监测日报", title_style))
    content.append(Paragraph(f"报告日期：{today}", subtitle_style))
    content.append(Spacer(1, 20))
    
    # 1. 市场指数表现
    content.append(Paragraph("1. 市场指数表现", subtitle_style))
    index_fig = get_latest_figure("index_performance_*.png")
    if index_fig:
        img = Image(index_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图1: 主要市场指数涨跌幅对比", caption_style))
    
    content.append(Spacer(1, 15))
    
    # 2. 行业资金流向
    content.append(Paragraph("2. 行业资金流向分析", subtitle_style))
    industry_fig = get_latest_figure("industry_moneyflow_top_bottom_*.png")
    if industry_fig:
        img = Image(industry_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图2: 行业资金流向排行榜（净流入/净流出前十）", caption_style))
    
    content.append(Spacer(1, 15))
    
    # 3. 全市场个股资金净流入
    content.append(Paragraph("3. 全市场个股资金净流入排行", subtitle_style))
    
    # 资金净流入排行图
    inflow_fig = get_latest_figure("market_net_inflow_top_*.png")
    if inflow_fig:
        img = Image(inflow_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图3: 全市场个股资金净流入金额排行榜（前十名）", caption_style))
    
    # 资金净流入率排行图
    inflow_rate_fig = get_latest_figure("market_inflow_rate_top_*.png")
    if inflow_rate_fig:
        img = Image(inflow_rate_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图4: 全市场个股资金净流入率排行榜（前十名）", caption_style))
    
    content.append(Spacer(1, 15))
    
    # 4. 量价背离指数分析
    content.append(Paragraph("4. 量价背离指数分析", subtitle_style))
    divergence_fig = get_latest_figure("price_volume_divergence_index_*.png")
    if divergence_fig:
        img = Image(divergence_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图5: 量价背离指数历史走势（过去20个交易日）", caption_style))
        content.append(Paragraph("说明: 该指数计算涨幅前50但资金净流出的个股占比，反映市场虚涨风险。指数超过30%时警示市场可能回调。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 5. 资金集中度指标分析
    content.append(Paragraph("5. 资金集中度指标分析", subtitle_style))
    concentration_fig = get_latest_figure("capital_concentration_index_*.png")
    if concentration_fig:
        img = Image(concentration_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图6: 资金集中度指标历史走势（过去20个交易日）", caption_style))
        content.append(Paragraph("说明: 该指标计算前10%个股的资金净流入占全市场比例，反映市场资金分散/集中程度。集中度越高说明市场情绪越分化，热点集中。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 6. 上涨/下跌股票比值分析
    content.append(Paragraph("6. 上涨/下跌股票比值分析", subtitle_style))
    up_down_ratio_fig = get_latest_figure("up_down_ratio_*.png")
    if up_down_ratio_fig:
        img = Image(up_down_ratio_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图7: 上涨/下跌股票比值历史走势（过去20个交易日）", caption_style))
        content.append(Paragraph("说明: 该指标计算市场上涨股票数与下跌股票数的比值。比值小于1表示下跌家数多于上涨家数，市场整体偏弱。比值大于2表示上涨家数远多于下跌家数，可能处于强势上涨中。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 7. 技术指标分析
    content.append(Paragraph("7. 技术指标分析", subtitle_style))
    tech_fig = get_latest_figure("market_rsi_analysis_*.png")
    if tech_fig:
        img = Image(tech_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图8: 上证指数RSI技术指标分析", caption_style))
        content.append(Paragraph("说明: RSI(相对强弱指数)指标显示超买超卖信号。当RSI>70时市场可能超买，<30时可能超卖。观察价格与RSI的背离，例如价格创新高但RSI未创新高可能信号顶部形成；价格创新低但RSI未创新低可能信号底部形成。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 8. 涨停板晋级率分析
    content.append(Paragraph("8. 涨停板晋级率分析", subtitle_style))
    promotion_fig = get_latest_figure("limit_promotion_rate_*.png")
    if promotion_fig:
        img = Image(promotion_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图9: 涨停板晋级率趋势（过去30个交易日）", caption_style))
        content.append(Paragraph("说明: 1进2晋级率是前一天首板涨停、当天再次涨停的股票数占比，中性区间为10%-20%。2进3晋级率是前一天二连板、当天再次涨停的股票数占比，中性区间为30%-40%。晋级率越高表示市场热度越高、赚钱效应越强。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 9. 新高/新低股票数分析
    content.append(Paragraph("9. 新高/新低股票数分析", subtitle_style))
    
    # 52周新高/新低图
    high_low_52w_fig = get_latest_figure("high_low_52w_*.png")
    if high_low_52w_fig:
        img = Image(high_low_52w_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图10: 52周新高/新低股票数趋势（过去30个交易日）", caption_style))
    
    # 26周新高/新低图
    high_low_26w_fig = get_latest_figure("high_low_26w_*.png")
    if high_low_26w_fig:
        img = Image(high_low_26w_fig, width=6.5*inch, height=3.5*inch)
        content.append(img)
        content.append(Spacer(1, 5))
        content.append(Paragraph("图11: 26周新高/新低股票数趋势（过去30个交易日）", caption_style))
        content.append(Paragraph("说明: 新高/新低股票数量反映市场健康程度。在上涨行情中，新高数量持续增加表示上涨动能强劲；新高数量减少但指数创新高可能暗示市场即将见顶。在下跌行情中，新低数量持续增加表示卖压沉重；新低数量明显减少可能表明市场接近底部。", note_style))
    
    content.append(Spacer(1, 15))
    
    # 10. 结论
    content.append(Paragraph("10. 市场监测结论", subtitle_style))
    
    conclusion_text = """
    基于以上分析，我们对当前市场状况得出以下结论：
    
    1. 大盘指数表现：关注沪深300、上证指数的强弱变化，以及创业板、科创板的表现差异。
    
    2. 行业资金流向：识别主导市场方向的强势行业，特别关注连续获得资金流入的行业。
    
    3. 个股资金流向：重点关注大额资金净流入的个股，它们往往代表着市场的主流方向。
    
    4. 量价背离指数：警惕虚假上涨行情，当价格上涨但资金流出时，增加风险控制。
    
    5. 资金集中度：评估市场是否存在明显热点，集中度过高时注意热点轮动风险。
    
    6. 上涨/下跌比例：全面了解市场整体强弱，作为重要的市场宽度指标。
    
    7. RSI技术指标：通过监测RSI超买超卖区域及背离现象，识别潜在的市场顶底位置。
    
    8. 涨停板晋级率：通过跟踪连板效应评估市场强度，晋级率高低反映市场赚钱效应。
    
    9. 新高/新低股票数：观察市场结构健康程度，新高数减少或新低数增多往往是市场转向的先导信号。
    
    综合判断：通过以上九个维度的综合分析，形成对市场的整体研判，指导投资决策。
    """
    
    content.append(Paragraph(conclusion_text, normal_style))
    
    # 添加页眉页脚
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"第 {page_num} 页"
        canvas.setFont(chinese_font, 9)
        canvas.drawRightString(7.5 * inch, 0.5 * inch, text)
        canvas.drawString(0.5 * inch, 0.5 * inch, "股票市场监测系统 - 自动生成报告")
        
        # 在页眉添加日期
        canvas.drawRightString(7.5 * inch, 10.5 * inch, today)
    
    # 构建PDF
    doc.build(content, onFirstPage=add_page_number, onLaterPages=add_page_number)
    
    print(f"PDF报告已生成: {output_filename}")
    print(f"如果报告中出现中文乱码，请检查系统中的中文字体是否正确安装")
    
    return output_filename

if __name__ == "__main__":
    # 测试生成PDF报告
    pdf_file = create_pdf_report("test_report.pdf")
    print(f"报告已生成: {pdf_file}") 