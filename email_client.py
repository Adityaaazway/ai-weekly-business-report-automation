import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# --- Load credentials from local config (not committed to GitHub) ---
try:
    from config_local import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER
except ImportError:
    EMAIL_SENDER = "you@example.com"
    EMAIL_PASSWORD = "YOUR_GMAIL_APP_PASSWORD_HERE"
    EMAIL_RECEIVER = "recipient@example.com"


def _format_currency(value):
    try:
        if value is None:
            return "N/A"
        return f"₹{float(value):,.0f}"
    except Exception:
        return "N/A"


def _format_number(value):
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


def _pct_change(current, previous):
    try:
        if current is None or previous is None:
            return "N/A"
        current = float(current)
        previous = float(previous)
        if previous == 0:
            return "N/A"
        change = ((current - previous) / previous) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.1f}%"
    except Exception:
        return "N/A"


def _report_text_to_html(report_text):
    if not report_text:
        return "<p style='margin:0;color:#374151;font-size:14px;line-height:1.7;'>No AI summary available.</p>"

    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    html_parts = []

    for line in lines:
        clean = line.strip()

        if clean.startswith("- "):
            html_parts.append(
                f"<li style='margin:0 0 8px 18px; color:#374151; font-size:14px; line-height:1.6;'>{clean[2:]}</li>"
            )
        else:
            html_parts.append(
                f"<p style='margin:0 0 12px 0; color:#374151; font-size:14px; line-height:1.7;'>{clean}</p>"
            )

    final_html = []
    in_list = False

    for block in html_parts:
        if block.startswith("<li"):
            if not in_list:
                final_html.append("<ul style='padding:0; margin:0 0 12px 0;'>")
                in_list = True
            final_html.append(block)
        else:
            if in_list:
                final_html.append("</ul>")
                in_list = False
            final_html.append(block)

    if in_list:
        final_html.append("</ul>")

    return "".join(final_html)


def _build_html_email(report_text, summary, chart_cids):
    latest = summary.get("latest_week", {}).get("basic_kpis", {})
    previous = summary.get("previous_week", {}).get("basic_kpis", {})

    latest_revenue = latest.get("total_revenue", 0)
    previous_revenue = previous.get("total_revenue", 0)

    latest_orders = latest.get("total_orders", 0)
    previous_orders = previous.get("total_orders", 0)

    latest_aov = latest.get("aov", None)
    previous_aov = previous.get("aov", None)

    revenue_change = _pct_change(latest_revenue, previous_revenue)
    orders_change = _pct_change(latest_orders, previous_orders)
    aov_change = _pct_change(latest_aov, previous_aov)

    ai_summary_html = _report_text_to_html(report_text)

    revenue_img = (
        f"<img src='cid:{chart_cids['revenue_wow']}' alt='Revenue chart' width='100%' "
        f"style='display:block; width:100%; max-width:100%; border:0; border-radius:12px;'>"
        if "revenue_wow" in chart_cids else ""
    )

    orders_img = (
        f"<img src='cid:{chart_cids['orders_wow']}' alt='Orders chart' width='100%' "
        f"style='display:block; width:100%; max-width:100%; border:0; border-radius:12px;'>"
        if "orders_wow" in chart_cids else ""
    )

    trend_img = (
        f"<img src='cid:{chart_cids['daily_revenue_trend']}' alt='Daily revenue trend chart' width='100%' "
        f"style='display:block; width:100%; max-width:100%; border:0; border-radius:12px;'>"
        if "daily_revenue_trend" in chart_cids else ""
    )

    channel_img = (
        f"<img src='cid:{chart_cids['channel_mix']}' alt='Channel mix chart' width='100%' "
        f"style='display:block; width:100%; max-width:100%; border:0; border-radius:12px;'>"
        if "channel_mix" in chart_cids else ""
    )

    top_products_img = (
        f"<img src='cid:{chart_cids['top_products']}' alt='Top products chart' width='100%' "
        f"style='display:block; width:100%; max-width:100%; border:0; border-radius:12px;'>"
        if "top_products" in chart_cids else ""
    )

    html = f"""
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body, table, td, p, a {{
            font-family: Arial, sans-serif;
          }}

          @media screen and (max-width: 640px) {{
            .container {{
              width: 100% !important;
              max-width: 100% !important;
              border-radius: 0 !important;
            }}

            .content-pad {{
              padding-left: 16px !important;
              padding-right: 16px !important;
            }}

            .metric-col,
            .chart-col {{
              display: block !important;
              width: 100% !important;
            }}

            .hero-title {{
              font-size: 24px !important;
              line-height: 1.3 !important;
            }}
          }}

          .ai-summary h1,
          .ai-summary h2,
          .ai-summary h3,
          .ai-summary h4,
          .ai-summary h5,
          .ai-summary h6,
          .ai-summary b,
          .ai-summary strong {{
            font-weight: bold !important;
            color: #111827 !important;
          }}

          .ai-summary p {{
            margin: 0 0 12px 0 !important;
          }}

          .ai-summary ul,
          .ai-summary ol {{
            margin: 0 0 12px 20px !important;
            padding: 0 !important;
          }}

          .ai-summary li {{
            margin: 0 0 8px 0 !important;
          }}
        </style>
      </head>

      <body style="margin:0; padding:0; background-color:#f3f4f6; font-family:Arial, sans-serif;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#f3f4f6; margin:0; padding:24px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" class="container" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%; max-width:780px; background-color:#ffffff; border-radius:16px; overflow:hidden;">

                <tr>
                  <td style="background-color:#1F4E79; padding:28px 32px;" class="content-pad">
                    <p style="margin:0; color:#dbeafe; font-size:12px; letter-spacing:1px; text-transform:uppercase; font-weight:bold;">Weekly Report</p>
                    <h1 class="hero-title" style="margin:8px 0 0 0; color:#ffffff; font-size:30px; line-height:1.2; font-weight:bold;">
                      {summary['week_start']} to {summary['week_end']}
                    </h1>
                  </td>
                </tr>

                <tr>
                  <td style="padding:24px 32px 8px 32px;" class="content-pad">
                    <p style="margin:0; color:#111827; font-size:20px; font-weight:bold;">Key Metrics</p>
                  </td>
                </tr>

                <tr>
                  <td style="padding:8px 20px 8px 20px;" class="content-pad">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td class="metric-col" width="33.33%" valign="top" style="padding:12px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:16px;">
                                <p style="margin:0 0 8px 0; color:#6b7280; font-size:12px; font-weight:bold;">Revenue</p>
                                <p style="margin:0; color:#111827; font-size:28px; font-weight:bold;">{_format_currency(latest_revenue)}</p>
                                <p style="margin:8px 0 0 0; color:#2E8B57; font-size:13px; font-weight:bold;">WoW: {revenue_change}</p>
                              </td>
                            </tr>
                          </table>
                        </td>

                        <td class="metric-col" width="33.33%" valign="top" style="padding:12px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:16px;">
                                <p style="margin:0 0 8px 0; color:#6b7280; font-size:12px; font-weight:bold;">Orders</p>
                                <p style="margin:0; color:#111827; font-size:28px; font-weight:bold;">{_format_number(latest_orders)}</p>
                                <p style="margin:8px 0 0 0; color:#2E8B57; font-size:13px; font-weight:bold;">WoW: {orders_change}</p>
                              </td>
                            </tr>
                          </table>
                        </td>

                        <td class="metric-col" width="33.33%" valign="top" style="padding:12px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:16px;">
                                <p style="margin:0 0 8px 0; color:#6b7280; font-size:12px; font-weight:bold;">AOV</p>
                                <p style="margin:0; color:#111827; font-size:28px; font-weight:bold;">{_format_currency(latest_aov)}</p>
                                <p style="margin:8px 0 0 0; color:#2E8B57; font-size:13px; font-weight:bold;">WoW: {aov_change}</p>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <tr>
                  <td style="padding:16px 32px 8px 32px;" class="content-pad">
                    <p style="margin:0; color:#111827; font-size:20px; font-weight:bold;">AI Summary</p>
                  </td>
                </tr>

                <tr>
                  <td style="padding:8px 32px 8px 32px;" class="content-pad">
                    <div class="ai-summary" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px; padding:18px; color:#374151; font-size:15px; line-height:1.7;">
                      {ai_summary_html}
                    </div>
                  </td>
                </tr>

                <tr>
                  <td style="padding:16px 32px 8px 32px;" class="content-pad">
                    <p style="margin:0; color:#111827; font-size:20px; font-weight:bold;">Charts</p>
                  </td>
                </tr>

                <tr>
                  <td style="padding:8px 24px 8px 24px;" class="content-pad">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td class="chart-col" width="50%" valign="top" style="padding:8px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:12px;">
                                {revenue_img}
                              </td>
                            </tr>
                          </table>
                        </td>

                        <td class="chart-col" width="50%" valign="top" style="padding:8px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:12px;">
                                {trend_img}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td class="chart-col" width="50%" valign="top" style="padding:8px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:12px;">
                                {channel_img}
                              </td>
                            </tr>
                          </table>
                        </td>

                        <td class="chart-col" width="50%" valign="top" style="padding:8px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:12px;">
                                {top_products_img}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td colspan="2" style="padding:8px;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:12px;">
                            <tr>
                              <td style="padding:12px;">
                                {orders_img}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <tr>
                  <td style="padding:18px 32px; background:#f9fafb; border-top:1px solid #e5e7eb;" class="content-pad">
                    <p style="margin:0; color:#6b7280; font-size:12px;">Automated weekly business report generated from pipeline data.</p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    return html


def send_email(report_text, summary, chart_paths):
    """
    Sends the weekly report via Gmail SMTP with HTML + inline charts.
    """
    try:
        subject = f"Weekly Report: {summary['week_start']} to {summary['week_end']}"

        msg = MIMEMultipart("related")
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg["Subject"] = subject

        alt_part = MIMEMultipart("alternative")
        msg.attach(alt_part)

        plain_text = report_text if report_text else "Weekly report generated successfully."
        alt_part.attach(MIMEText(plain_text, "plain", "utf-8"))

        chart_cids = {key: key for key in chart_paths}

        html_body = _build_html_email(report_text, summary, chart_cids)
        alt_part.attach(MIMEText(html_body, "html", "utf-8"))

        for key, path in chart_paths.items():
            if not path or not os.path.exists(path):
                continue

            mime_type, _ = mimetypes.guess_type(path)
            if mime_type and mime_type.startswith("image"):
                with open(path, "rb") as f:
                    img = MIMEImage(f.read())

                img.add_header("Content-ID", f"<{chart_cids[key]}>")
                img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
                msg.attach(img)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("HTML email sent successfully.")

    except Exception as e:
        print("CRITICAL ERROR: Failed to send email.")
        print(type(e).__name__, str(e))
        raise