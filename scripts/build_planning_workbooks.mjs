import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = new URL("../outputs/autobiz-blueprint/", import.meta.url).pathname;
const previewDir = "/tmp/autobiz-workbook-previews/";
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const colors = {
  navy: "#17324D",
  blue: "#2F6B9A",
  paleBlue: "#DCEAF5",
  teal: "#167D78",
  paleTeal: "#DDF2EF",
  gold: "#D9A441",
  paleGold: "#FFF2CC",
  red: "#B54747",
  paleRed: "#FCE8E6",
  green: "#387A4A",
  paleGreen: "#E2F0D9",
  gray: "#64748B",
  paleGray: "#EEF2F6",
  white: "#FFFFFF",
};

function title(sheet, range, text, subtitle) {
  const titleRange = sheet.getRange(range);
  titleRange.merge();
  titleRange.values = [[text]];
  titleRange.format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white, size: 18 },
    verticalAlignment: "center",
  };
  titleRange.format.rowHeight = 34;
  if (subtitle) {
    const row = Number(range.match(/\d+/)[0]) + 1;
    const endCol = range.split(":")[1].replace(/\d+/g, "");
    const sub = sheet.getRange(`A${row}:${endCol}${row}`);
    sub.merge();
    sub.values = [[subtitle]];
    sub.format = { fill: colors.paleBlue, font: { color: colors.navy, italic: true }, wrapText: true };
    sub.format.rowHeight = 30;
  }
}

function section(sheet, range, text) {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[text]];
  r.format = { fill: colors.blue, font: { bold: true, color: colors.white } };
}

function header(range) {
  range.format = {
    fill: colors.navy,
    font: { bold: true, color: colors.white },
    borders: { preset: "inside", style: "thin", color: "#8FA5B8" },
    wrapText: true,
    verticalAlignment: "center",
  };
}

function input(range, numberFormat) {
  range.format = {
    fill: colors.paleGold,
    font: { color: "#1D4ED8" },
    borders: { preset: "outside", style: "thin", color: colors.gold },
  };
  if (numberFormat) range.format.numberFormat = numberFormat;
}

function output(range, numberFormat) {
  range.format = { fill: colors.paleTeal, font: { bold: true, color: colors.navy } };
  if (numberFormat) range.format.numberFormat = numberFormat;
}

async function exportAndPreview(workbook, filename, sheets) {
  for (const { name, range } of sheets) {
    const blob = await workbook.render({ sheetName: name, range, scale: 1, format: "png" });
    await fs.writeFile(`${previewDir}${filename}-${name.replaceAll(" ", "-")}.png`, new Uint8Array(await blob.arrayBuffer()));
  }
  const file = await SpreadsheetFile.exportXlsx(workbook);
  await file.save(`${outputDir}${filename}.xlsx`);
}

async function buildFinancialModel() {
  const wb = Workbook.create();
  const summary = wb.worksheets.add("Summary");
  const assumptions = wb.worksheets.add("Assumptions");
  const forecast = wb.worksheets.add("Forecast");
  const checks = wb.worksheets.add("Checks");

  for (const s of [summary, assumptions, forecast, checks]) s.showGridLines = false;

  title(summary, "A1:M1", "Autobiz Financial Model", "Illustrative 12-month planning model — inputs are hypotheses, not market evidence");
  summary.getRange("A4:B9").values = [
    ["Planning scenario", "Base"],
    ["Year 1 revenue", null],
    ["Year 1 contribution", null],
    ["Contribution margin", null],
    ["Ending cash", null],
    ["Break-even month", null],
  ];
  summary.getRange("B5").formulas = [["=SUM('Forecast'!B9:M9)"]];
  summary.getRange("B6").formulas = [["=SUM('Forecast'!B18:M18)"]];
  summary.getRange("B7").formulas = [["=IFERROR(B6/B5,0)"]];
  summary.getRange("B8").formulas = [["='Forecast'!M24"]];
  summary.getRange("B9").formulas = [["=IFERROR(INDEX('Forecast'!B3:M3,1,MATCH(TRUE,'Forecast'!B21:M21>=0,0)),\"Not in year 1\")"]];
  header(summary.getRange("A4:B4"));
  output(summary.getRange("B5:B8"));
  summary.getRange("B5:B6").format.numberFormat = '€#,##0;[Red](€#,##0);-';
  summary.getRange("B7").format.numberFormat = "0.0%";
  summary.getRange("B8").format.numberFormat = '€#,##0;[Red](€#,##0);-';
  summary.getRange("A11:D11").values = [["Month", "Revenue", "Contribution", "Closing cash"]];
  summary.getRange("A12:A23").values = Array.from({ length: 12 }, (_, i) => [`M${i + 1}`]);
  summary.getRange("B12:D12").formulas = [["='Forecast'!B9", "='Forecast'!B18", "='Forecast'!B24"]];
  for (let row = 13; row <= 23; row++) {
    const col = String.fromCharCode(66 + row - 12);
    summary.getRange(`B${row}:D${row}`).formulas = [[`='Forecast'!${col}9`, `='Forecast'!${col}18`, `='Forecast'!${col}24`]];
  }
  header(summary.getRange("A11:D11"));
  summary.getRange("B12:D23").format.numberFormat = '€#,##0;[Red](€#,##0);-';
  const cashChart = summary.charts.add("line", summary.getRange("A11:D23"));
  cashChart.title = "Revenue, contribution and cash (€)";
  cashChart.hasLegend = true;
  cashChart.xAxis = { axisType: "textAxis" };
  cashChart.yAxis = { numberFormatCode: "€#,##0" };
  cashChart.setPosition("F4", "M23");
  summary.getRange("A4:A9").format.font = { bold: true, color: colors.navy };
  summary.getRange("A1:M23").format.font.name = "Aptos";
  summary.getRange("A:A").format.columnWidth = 24;
  summary.getRange("B:M").format.columnWidth = 12;
  summary.freezePanes.freezeRows(2);

  title(assumptions, "A1:F1", "Assumptions", "Blue text on gold cells indicates editable hypotheses");
  assumptions.getRange("A4:F4").values = [["Driver", "Base", "Conservative", "Upside", "Unit", "Basis / note"]];
  assumptions.getRange("A5:F18").values = [
    ["Starting customers", 0, 0, 0, "customers", "Pre-revenue starting point"],
    ["New customers in month 1", 1, 0, 2, "customers", "Hypothesis to validate"],
    ["Monthly new-customer growth", 0.15, 0.05, 0.25, "%", "Hypothesis to validate"],
    ["Monthly customer churn", 0.03, 0.06, 0.02, "%", "Hypothesis to validate"],
    ["Monthly subscription price", 750, 500, 1000, "EUR/customer", "Hypothesis to test through paid offers"],
    ["One-time setup fee", 1000, 500, 1500, "EUR/new customer", "Hypothesis to test through paid offers"],
    ["Variable delivery hours/customer", 3, 5, 2, "hours/month", "Includes operator time"],
    ["Loaded hourly delivery cost", 50, 50, 50, "EUR/hour", "Opportunity cost or contractor rate"],
    ["AI/API cost/customer", 25, 40, 20, "EUR/month", "Placeholder until measured"],
    ["Payment and variable fees", 0.03, 0.035, 0.025, "% revenue", "Illustrative blended variable fee"],
    ["Fixed software and hosting", 250, 300, 300, "EUR/month", "Placeholder until vendors selected"],
    ["Sales and marketing", 500, 300, 1000, "EUR/month", "Founder-led initially"],
    ["Other administration", 250, 300, 350, "EUR/month", "Accounting, insurance, tools estimate"],
    ["Opening cash", 10000, 10000, 10000, "EUR", "Planning input"],
  ];
  header(assumptions.getRange("A4:F4"));
  input(assumptions.getRange("B5:D18"));
  assumptions.getRange("B7:D8").format.numberFormat = "0.0%";
  assumptions.getRange("B14:D14").format.numberFormat = "0.0%";
  assumptions.getRange("B9:D10").format.numberFormat = '€#,##0';
  assumptions.getRange("B12:D13").format.numberFormat = '€#,##0';
  assumptions.getRange("B15:D18").format.numberFormat = '€#,##0';
  assumptions.getRange("A20:F23").values = [
    ["Instructions", null, null, null, null, null],
    ["1", "Replace hypotheses with interview and pilot evidence.", null, null, null, null],
    ["2", "Keep founder/operator time in variable cost; do not treat it as free.", null, null, null, null],
    ["3", "The forecast currently uses the Base column. Scenarios are comparison inputs.", null, null, null, null],
  ];
  section(assumptions, "A20:F20", "Instructions");
  assumptions.getRange("B21:F23").merge(true);
  assumptions.getRange("A1:F23").format.font.name = "Aptos";
  assumptions.getRange("A:A").format.columnWidth = 34;
  assumptions.getRange("B:D").format.columnWidth = 16;
  assumptions.getRange("E:E").format.columnWidth = 18;
  assumptions.getRange("F:F").format.columnWidth = 46;
  assumptions.freezePanes.freezeRows(4);

  title(forecast, "A1:M1", "12-Month Forecast", "Formula-driven from Base assumptions");
  forecast.getRange("A3:M3").values = [["Metric", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"]];
  header(forecast.getRange("A3:M3"));
  const labels = [
    ["Opening customers"], ["New customers"], ["Churned customers"], ["Closing customers"], [""],
    ["Revenue"], ["  Subscription revenue"], ["  Setup revenue"], [""],
    ["Variable costs"], ["  Delivery labor"], ["  AI/API usage"], ["  Payment/variable fees"], [""],
    ["Contribution"], ["Contribution margin"], ["Fixed operating costs"], ["Operating cash flow"], [""],
    ["Opening cash"], ["Closing cash"],
  ];
  forecast.getRange("A4:A24").values = labels;
  forecast.getRange("B4").formulas = [["='Assumptions'!B5"]];
  forecast.getRange("C4:M4").formulas = [[...Array.from({ length: 11 }, (_, i) => `=${String.fromCharCode(66 + i)}7`)]];
  forecast.getRange("B5").formulas = [["='Assumptions'!B6"]];
  forecast.getRange("C5").formulas = [["=MAX(0,ROUND(B5*(1+'Assumptions'!$B$7),0))"]];
  forecast.getRange("C5:M5").fillRight();
  forecast.getRange("B6").formulas = [["=MIN(B4,ROUND(B4*'Assumptions'!$B$8,0))"]];
  forecast.getRange("B6:M6").fillRight();
  forecast.getRange("B7").formulas = [["=B4+B5-B6"]];
  forecast.getRange("B7:M7").fillRight();
  forecast.getRange("B9").formulas = [["=SUM(B10:B11)"]];
  forecast.getRange("B9:M9").fillRight();
  forecast.getRange("B10").formulas = [["=B7*'Assumptions'!$B$9"]];
  forecast.getRange("B10:M10").fillRight();
  forecast.getRange("B11").formulas = [["=B5*'Assumptions'!$B$10"]];
  forecast.getRange("B11:M11").fillRight();
  forecast.getRange("B13").formulas = [["=SUM(B14:B16)"]];
  forecast.getRange("B13:M13").fillRight();
  forecast.getRange("B14").formulas = [["=B7*'Assumptions'!$B$11*'Assumptions'!$B$12"]];
  forecast.getRange("B14:M14").fillRight();
  forecast.getRange("B15").formulas = [["=B7*'Assumptions'!$B$13"]];
  forecast.getRange("B15:M15").fillRight();
  forecast.getRange("B16").formulas = [["=B9*'Assumptions'!$B$14"]];
  forecast.getRange("B16:M16").fillRight();
  forecast.getRange("B18").formulas = [["=B9-B13"]];
  forecast.getRange("B18:M18").fillRight();
  forecast.getRange("B19").formulas = [["=IFERROR(B18/B9,0)"]];
  forecast.getRange("B19:M19").fillRight();
  forecast.getRange("B20").formulas = [["=SUM('Assumptions'!$B$15:$B$17)"]];
  forecast.getRange("B20:M20").fillRight();
  forecast.getRange("B21").formulas = [["=B18-B20"]];
  forecast.getRange("B21:M21").fillRight();
  forecast.getRange("B23").formulas = [["='Assumptions'!$B$18"]];
  forecast.getRange("C23:M23").formulas = [[...Array.from({ length: 11 }, (_, i) => `=${String.fromCharCode(66 + i)}24`)]];
  forecast.getRange("B24").formulas = [["=B23+B21"]];
  forecast.getRange("B24:M24").fillRight();
  forecast.getRange("A9:M9").format = { fill: colors.paleBlue, font: { bold: true, color: colors.navy }, borders: { preset: "doubleBottom", style: "double", color: colors.navy } };
  forecast.getRange("A18:M18").format = { fill: colors.paleTeal, font: { bold: true, color: colors.navy } };
  forecast.getRange("A21:M21").format = { fill: colors.paleGold, font: { bold: true, color: colors.navy } };
  forecast.getRange("A24:M24").format = { fill: colors.paleBlue, font: { bold: true, color: colors.navy }, borders: { preset: "doubleBottom", style: "double", color: colors.navy } };
  forecast.getRange("B4:M7").format.numberFormat = "#,##0";
  forecast.getRange("B9:M18").format.numberFormat = '€#,##0;[Red](€#,##0);-';
  forecast.getRange("B19:M19").format.numberFormat = "0.0%";
  forecast.getRange("B20:M24").format.numberFormat = '€#,##0;[Red](€#,##0);-';
  forecast.getRange("A1:M24").format.font.name = "Aptos";
  forecast.getRange("A:A").format.columnWidth = 28;
  forecast.getRange("B:M").format.columnWidth = 12;
  forecast.freezePanes.freezeRows(3);
  forecast.freezePanes.freezeColumns(1);

  title(checks, "A1:G1", "Model Checks", "PASS means formulas reconcile; assumptions remain unvalidated");
  checks.getRange("A4:G4").values = [["Check", "Actual", "Expected", "Difference", "Tolerance", "Status", "Where to fix / note"]];
  checks.getRange("A5:G9").values = [
    ["Revenue equals components", null, 0, null, 0.01, null, "Forecast rows 9–11"],
    ["Variable costs equal components", null, 0, null, 0.01, null, "Forecast rows 13–16"],
    ["Customer roll-forward", null, 0, null, 0.01, null, "Forecast rows 4–7"],
    ["Cash roll-forward", null, 0, null, 0.01, null, "Forecast rows 21–24"],
    ["All required base assumptions populated", null, 14, null, 0, null, "Assumptions B5:B18"],
  ];
  checks.getRange("B5").formulas = [["=SUM('Forecast'!B9:M9)-SUM('Forecast'!B10:M10)-SUM('Forecast'!B11:M11)"]];
  checks.getRange("B6").formulas = [["=SUM('Forecast'!B13:M13)-SUM('Forecast'!B14:M14)-SUM('Forecast'!B15:M15)-SUM('Forecast'!B16:M16)"]];
  checks.getRange("B7").formulas = [["=SUM('Forecast'!B7:M7)-SUM('Forecast'!B4:M4)-SUM('Forecast'!B5:M5)+SUM('Forecast'!B6:M6)"]];
  checks.getRange("B8").formulas = [["=SUM('Forecast'!B24:M24)-SUM('Forecast'!B23:M23)-SUM('Forecast'!B21:M21)"]];
  checks.getRange("B9").formulas = [["=COUNT('Assumptions'!B5:B18)"]];
  checks.getRange("D5").formulas = [["=B5-C5"]];
  checks.getRange("D5:D9").fillDown();
  checks.getRange("F5").formulas = [["=IF(ABS(D5)<=E5,\"PASS\",\"FAIL\")"]];
  checks.getRange("F5:F9").fillDown();
  checks.getRange("A11:B12").values = [["MODEL STATUS", null], ["Interpretation", "Calculation integrity only; validate all gold inputs."]];
  checks.getRange("B11").formulas = [["=IF(COUNTIF(F5:F9,\"FAIL\")=0,\"PASS\",\"FAIL\")"]];
  header(checks.getRange("A4:G4"));
  output(checks.getRange("B11"));
  checks.getRange("B5:E8").format.numberFormat = '€#,##0.00;[Red](€#,##0.00);-';
  checks.getRange("A1:G12").format.font.name = "Aptos";
  checks.getRange("A:A").format.columnWidth = 34;
  checks.getRange("B:F").format.columnWidth = 16;
  checks.getRange("G:G").format.columnWidth = 36;
  checks.freezePanes.freezeRows(4);

  await exportAndPreview(wb, "autobiz-financial-model", [
    { name: "Summary", range: "A1:M23" },
    { name: "Assumptions", range: "A1:F23" },
    { name: "Forecast", range: "A1:M24" },
    { name: "Checks", range: "A1:G12" },
  ]);

  const summaryCheck = await wb.inspect({ kind: "table", range: "Summary!A1:M23", include: "values,formulas", tableMaxRows: 23, tableMaxCols: 13 });
  const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "financial model formula error scan" });
  console.log(summaryCheck.ndjson);
  console.log(errors.ndjson);
}

async function buildScorecard() {
  const wb = Workbook.create();
  const dashboard = wb.worksheets.add("Dashboard");
  const weekly = wb.worksheets.add("Weekly KPIs");
  const definitions = wb.worksheets.add("Definitions");
  const checks = wb.worksheets.add("Checks");
  for (const s of [dashboard, weekly, definitions, checks]) s.showGridLines = false;

  title(dashboard, "A1:H1", "Autobiz Operating Scorecard", "Weekly management view — enter actuals on the Weekly KPIs sheet");
  dashboard.getRange("A4:H4").values = [["Metric", "Latest", "Target", "Status", "Unit", "Owner", "Why it matters", "Source"]];
  const metrics = [
    ["Customer interviews", null, 5, null, "count/week", "Founder", "Market evidence", "Interview log"],
    ["Qualified leads", null, 3, null, "count/week", "Sales", "Demand quality", "CRM"],
    ["Proposal conversion", null, 0.3, null, "%", "Sales", "Offer effectiveness", "CRM"],
    ["Active paying customers", null, 3, null, "count", "Founder", "Commercial proof", "Billing"],
    ["Median first response", null, 60, null, "minutes", "Operations", "Service speed", "Workflow log"],
    ["Automation success", null, 0.9, null, "%", "Product", "Reliability", "Workflow log"],
    ["Exception rate", null, 0.15, null, "%", "Operations", "Human workload", "Workflow log"],
    ["Founder minutes/customer", null, 120, null, "minutes/week", "Founder", "Scalability", "Time log"],
    ["Contribution margin", null, 0.5, null, "%", "Finance", "Economic quality", "Financial model"],
    ["Customer churn", null, 0.03, null, "% monthly", "Customer success", "Retention", "Billing"],
  ];
  dashboard.getRange("A5:H14").values = metrics;
  for (let r = 5; r <= 14; r++) {
    dashboard.getRange(`B${r}`).formulas = [[`=IFERROR(LOOKUP(2,1/('Weekly KPIs'!B$5:B$56<>\"\"),'Weekly KPIs'!${String.fromCharCode(65 + (r - 4))}$5:${String.fromCharCode(65 + (r - 4))}$56),0)`]];
  }
  const statusSpecs = [
    [5, "B", ">=", "BELOW"], [6, "C", ">=", "BELOW"], [7, "D", ">=", "BELOW"],
    [8, "E", ">=", "BELOW"], [9, "F", "<=", "ABOVE"], [10, "G", ">=", "BELOW"],
    [11, "H", "<=", "ABOVE"], [12, "I", "<=", "ABOVE"], [13, "J", ">=", "BELOW"],
    [14, "K", "<=", "ABOVE"],
  ];
  for (const [row, sourceCol, operator, missLabel] of statusSpecs) {
    dashboard.getRange(`D${row}`).formulas = [[`=IF(COUNT('Weekly KPIs'!${sourceCol}5:${sourceCol}56)=0,\"NO DATA\",IF(B${row}${operator}C${row},\"ON TRACK\",\"${missLabel}\"))`]];
  }
  header(dashboard.getRange("A4:H4"));
  output(dashboard.getRange("B5:D14"));
  dashboard.getRange("B7:C7").format.numberFormat = "0.0%";
  dashboard.getRange("B10:C11").format.numberFormat = "0.0%";
  dashboard.getRange("B13:C14").format.numberFormat = "0.0%";
  dashboard.getRange("A17:C17").values = [["Week", "Interviews", "Qualified leads"]];
  for (let row = 18; row <= 29; row++) {
    const sourceRow = row - 13;
    dashboard.getRange(`A${row}:C${row}`).formulas = [[`=TEXT('Weekly KPIs'!A${sourceRow},\"yyyy-mm-dd\")`, `='Weekly KPIs'!B${sourceRow}`, `='Weekly KPIs'!C${sourceRow}`]];
  }
  const activityChart = dashboard.charts.add("line", dashboard.getRange("A17:C29"));
  activityChart.title = "Interviews and qualified leads (last 12 slots)";
  activityChart.hasLegend = true;
  activityChart.xAxis = { axisType: "textAxis" };
  activityChart.yAxis = { numberFormatCode: "0" };
  activityChart.setPosition("A32", "H47");
  dashboard.getRange("A1:H47").format.font.name = "Aptos";
  dashboard.getRange("A:A").format.columnWidth = 28;
  dashboard.getRange("B:D").format.columnWidth = 15;
  dashboard.getRange("E:F").format.columnWidth = 16;
  dashboard.getRange("G:H").format.columnWidth = 28;
  dashboard.freezePanes.freezeRows(4);

  title(weekly, "A1:L1", "Weekly KPI Input", "Gold cells are editable; use ISO week-ending dates");
  weekly.getRange("A4:L4").values = [["Week ending", "Interviews", "Qualified leads", "Proposal conversion", "Active customers", "Median first response", "Automation success", "Exception rate", "Founder minutes/customer", "Contribution margin", "Monthly churn", "Management note"]];
  header(weekly.getRange("A4:L4"));
  const rows = Array.from({ length: 52 }, (_, i) => [new Date(2026, 6, 31 + i * 7), null, null, null, null, null, null, null, null, null, null, ""]);
  weekly.getRange("A5:L56").values = rows;
  input(weekly.getRange("B5:L56"));
  weekly.getRange("A5:A56").format.numberFormat = "yyyy-mm-dd";
  weekly.getRange("D5:D56").format.numberFormat = "0.0%";
  weekly.getRange("G5:H56").format.numberFormat = "0.0%";
  weekly.getRange("J5:K56").format.numberFormat = "0.0%";
  weekly.getRange("A1:L56").format.font.name = "Aptos";
  weekly.getRange("A:A").format.columnWidth = 15;
  weekly.getRange("B:K").format.columnWidth = 17;
  weekly.getRange("L:L").format.columnWidth = 42;
  weekly.freezePanes.freezeRows(4);
  weekly.freezePanes.freezeColumns(1);

  title(definitions, "A1:G1", "KPI Definitions", "One definition per metric prevents misleading scorecards");
  definitions.getRange("A4:G4").values = [["Metric", "Definition", "Calculation", "Direction", "Cadence", "Owner", "Data source"]];
  definitions.getRange("A5:G14").values = [
    ["Customer interviews", "Completed structured problem interviews", "Count of completed records", "Higher during validation", "Weekly", "Founder", "Interview log"],
    ["Qualified leads", "Leads meeting documented fit criteria", "Count meeting policy", "Higher", "Weekly", "Sales", "CRM"],
    ["Proposal conversion", "Won proposals divided by decided proposals", "Won / (won + lost)", "Higher", "Rolling monthly", "Sales", "CRM"],
    ["Active paying customers", "Customers with active paid engagement", "Distinct active engagements", "Higher", "Weekly", "Founder", "Billing"],
    ["Median first response", "Median minutes from eligible enquiry to first response", "Median(response - received)", "Lower", "Weekly", "Operations", "Workflow log"],
    ["Automation success", "Runs completing without manual repair", "Successful automated runs / eligible runs", "Higher", "Weekly", "Product", "Workflow log"],
    ["Exception rate", "Runs requiring manual exception handling", "Exception runs / all runs", "Lower", "Weekly", "Operations", "Workflow log"],
    ["Founder minutes/customer", "Founder delivery and support time per active customer", "Tracked minutes / active customers", "Lower after quality stable", "Weekly", "Founder", "Time log"],
    ["Contribution margin", "Revenue less variable delivery costs", "Contribution / revenue", "Higher", "Monthly", "Finance", "Financial model"],
    ["Customer churn", "Customers lost divided by opening customers", "Lost / opening customers", "Lower", "Monthly", "Customer success", "Billing"],
  ];
  header(definitions.getRange("A4:G4"));
  definitions.getRange("A5:G14").format.wrapText = true;
  definitions.getRange("A1:G14").format.font.name = "Aptos";
  definitions.getRange("A:A").format.columnWidth = 28;
  definitions.getRange("B:C").format.columnWidth = 42;
  definitions.getRange("D:G").format.columnWidth = 20;
  definitions.freezePanes.freezeRows(4);

  title(checks, "A1:F1", "Scorecard Checks", "Integrity checks do not replace management interpretation");
  checks.getRange("A4:F4").values = [["Check", "Actual", "Expected", "Difference", "Status", "Note"]];
  checks.getRange("A5:F8").values = [
    ["Weekly date rows", null, 52, null, null, "Weekly KPIs A5:A56"],
    ["Unique KPI definitions", null, 10, null, null, "Definitions A5:A14"],
    ["Dashboard metric count", null, 10, null, null, "Dashboard A5:A14"],
    ["Targets populated", null, 10, null, null, "Dashboard C5:C14"],
  ];
  checks.getRange("B5").formulas = [["=COUNT('Weekly KPIs'!A5:A56)"]];
  checks.getRange("B6").formulas = [["=COUNTA('Definitions'!A5:A14)"]];
  checks.getRange("B7").formulas = [["=COUNTA('Dashboard'!A5:A14)"]];
  checks.getRange("B8").formulas = [["=COUNT('Dashboard'!C5:C14)"]];
  checks.getRange("D5").formulas = [["=B5-C5"]];
  checks.getRange("D5:D8").fillDown();
  checks.getRange("E5").formulas = [["=IF(D5=0,\"PASS\",\"FAIL\")"]];
  checks.getRange("E5:E8").fillDown();
  checks.getRange("A10:B10").values = [["MODEL STATUS", null]];
  checks.getRange("B10").formulas = [["=IF(COUNTIF(E5:E8,\"FAIL\")=0,\"PASS\",\"FAIL\")"]];
  header(checks.getRange("A4:F4"));
  output(checks.getRange("B10"));
  checks.getRange("A1:F10").format.font.name = "Aptos";
  checks.getRange("A:A").format.columnWidth = 32;
  checks.getRange("B:E").format.columnWidth = 16;
  checks.getRange("F:F").format.columnWidth = 34;

  await exportAndPreview(wb, "autobiz-operating-scorecard", [
    { name: "Dashboard", range: "A1:H47" },
    { name: "Weekly KPIs", range: "A1:L20" },
    { name: "Definitions", range: "A1:G14" },
    { name: "Checks", range: "A1:F10" },
  ]);
  const dashboardCheck = await wb.inspect({ kind: "table", range: "Dashboard!A1:H14", include: "values,formulas", tableMaxRows: 14, tableMaxCols: 8 });
  const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "scorecard formula error scan" });
  console.log(dashboardCheck.ndjson);
  console.log(errors.ndjson);
}

await buildFinancialModel();
await buildScorecard();
