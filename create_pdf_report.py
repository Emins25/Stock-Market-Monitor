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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import platform

def create_pdf_report(output_filename="Stock_Market_Monitor.pdf"):
    """
    创建市场监测PDF报告
    
    参数:
        output_filename: 输出的PDF文件名
    """
    # 注册中文字体
    # 根据不同操作系统选择合适的中文字体
    system = platform.system()
    if system == 'Windows':
        # Windows系统使用微软雅黑或宋体
        try:
            # 先尝试微软雅黑
            pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/msyh.ttc'))
            print("已注册字体: 微软雅黑")
        except:
            try:
                # 再尝试宋体
                pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/simsun.ttc'))
                print("已注册字体: 宋体")
            except Exception as e:
                # 最后尝试黑体
                try:
                    pdfmetrics.registerFont(TTFont('chinese_font', 'C:/Windows/Fonts/simhei.ttf'))
                    print("已注册字体: 黑体")
                except Exception as e:
                    print(f"注册中文字体失败: {e}")
                    print("请确保系统中安装了中文字体，PDF报告中的中文可能显示为乱码")
    elif system == 'Darwin':  # macOS
        try:
            # macOS系统使用苹方或华文黑体
            pdfmetrics.registerFont(TTFont('chinese_font', '/System/Library/Fonts/PingFang.ttc'))
            print("已注册字体: 苹方")
        except:
            try:
                pdfmetrics.registerFont(TTFont('chinese_font', '/System/Library/Fonts/STHeiti Light.ttc'))
                print("已注册字体: 华文黑体")
            except Exception as e:
                print(f"注册中文字体失败: {e}")
    else:  # Linux或其他系统
        try:
            # Linux系统尝试使用文泉驿或Noto Sans CJK
            pdfmetrics.registerFont(TTFont('chinese_font', '/usr/share/fonts/wenquanyi/wqy-microhei.ttc'))
            print("已注册字体: 文泉驿微米黑")
        except:
            try:
                pdfmetrics.registerFont(TTFont('chinese_font', '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'))
                print("已注册字体: Noto Sans CJK")
            except Exception as e:
                print(f"注册中文字体失败: {e}")
    
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
    
    # 创建自定义样式，使用已注册的中文字体
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='chinese_font',  # 使用注册的中文字体
        fontSize=24,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontName='chinese_font',  # 使用注册的中文字体
        fontSize=16,
        textColor=colors.darkblue,
        spaceBefore=10,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName='chinese_font',  # 使用注册的中文字体
        fontSize=10,
        spaceBefore=5,
        spaceAfter=5
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
        img = Image(index_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图1: 主要市场指数涨跌幅对比", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 2. 行业资金流向
    content.append(Paragraph("2. 行业资金流向分析", subtitle_style))
    industry_fig = get_latest_figure("industry_moneyflow_top_bottom_*.png")
    if industry_fig:
        img = Image(industry_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图2: 行业资金流向排行榜（净流入/净流出前十）", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 3. 全市场个股资金净流入
    content.append(Paragraph("3. 全市场个股资金净流入排行", subtitle_style))
    
    # 资金净流入排行图
    inflow_fig = get_latest_figure("market_net_inflow_top_*.png")
    if inflow_fig:
        img = Image(inflow_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图3: 全市场个股资金净流入金额排行榜（前十名）", normal_style))
    
    # 资金净流入率排行图
    inflow_rate_fig = get_latest_figure("market_inflow_rate_top_*.png")
    if inflow_rate_fig:
        img = Image(inflow_rate_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图4: 全市场个股资金净流入率排行榜（前十名）", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 4. 量价背离指数分析
    content.append(Paragraph("4. 量价背离指数分析", subtitle_style))
    divergence_fig = get_latest_figure("price_volume_divergence_index_*.png")
    if divergence_fig:
        img = Image(divergence_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图5: 量价背离指数历史走势（过去20个交易日）", normal_style))
        content.append(Paragraph("说明: 该指数计算涨幅前50但资金净流出的个股占比，反映市场虚涨风险。\n      指数超过30%时警示市场可能回调。", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 5. 资金集中度指标分析
    content.append(Paragraph("5. 资金集中度指标分析", subtitle_style))
    concentration_fig = get_latest_figure("capital_concentration_index_*.png")
    if concentration_fig:
        img = Image(concentration_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图6: 资金集中度指标历史走势（过去20个交易日）", normal_style))
        content.append(Paragraph("说明: 该指标计算前10%个股的资金净流入占全市场比例，反映市场资金分散/集中程度。\n      集中度越高说明市场情绪越分化，热点集中。", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 6. 上涨/下跌股票比值分析
    content.append(Paragraph("6. 上涨/下跌股票比值分析", subtitle_style))
    up_down_ratio_fig = get_latest_figure("up_down_ratio_*.png")
    if up_down_ratio_fig:
        img = Image(up_down_ratio_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图7: 上涨/下跌股票比值历史走势（过去20个交易日）", normal_style))
        content.append(Paragraph("说明: 该指标计算市场上涨股票数与下跌股票数的比值。\n      比值小于1表示下跌家数多于上涨家数，市场整体偏弱。\n      比值大于2表示上涨家数远多于下跌家数，可能处于强势上涨中。", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 7. 技术指标分析
    content.append(Paragraph("7. 技术指标分析", subtitle_style))
    tech_fig = get_latest_figure("market_technical_analysis_*.png")
    if tech_fig:
        img = Image(tech_fig, width=6*inch, height=4*inch)
        content.append(img)
        content.append(Spacer(1, 10))
        content.append(Paragraph("图8: 上证指数技术指标分析（MACD、RSI）", normal_style))
        content.append(Paragraph("说明: MACD指标通过快慢均线的交叉判断趋势变化，RSI指标显示超买超卖信号。\n      两者结合可预测潜在的市场顶部和底部。", normal_style))
    
    content.append(Spacer(1, 20))
    
    # 8. 结论
    content.append(Paragraph("8. 市场监测结论", subtitle_style))
    
    conclusion_text = """
    基于以上分析，我们对当前市场状况得出以下结论：
    
    1. 大盘指数表现：关注沪深300、上证指数的强弱变化，以及创业板、科创板的表现差异。
    
    2. 行业资金流向：识别主导市场方向的强势行业，特别关注连续获得资金流入的行业。
    
    3. 个股资金流向：重点关注大额资金净流入的个股，它们往往代表着市场的主流方向。
    
    4. 量价背离指数：警惕虚假上涨行情，当价格上涨但资金流出时，增加风险控制。
    
    5. 资金集中度：评估市场是否存在明显热点，集中度过高时注意热点轮动风险。
    
    6. 上涨/下跌比例：全面了解市场整体强弱，作为重要的市场宽度指标。
    
    7. 技术指标：通过MACD和RSI判断市场顶底，指导短期交易决策。
    
    综合判断：通过以上七个维度的综合分析，形成对市场的整体研判，指导投资决策。
    """
    
    content.append(Paragraph(conclusion_text, normal_style))
    
    # 构建PDF
    doc.build(content)
    
    print(f"PDF报告已生成: {output_filename}")
    print(f"如果报告中出现中文乱码，请检查系统中的中文字体是否正确安装")
    
    return output_filename

if __name__ == "__main__":
    # 测试生成PDF报告
    pdf_file = create_pdf_report("test_report.pdf")
    print(f"报告已生成: {pdf_file}") 