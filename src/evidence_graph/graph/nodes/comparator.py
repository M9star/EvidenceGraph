from evidence_graph.state import Comparison, ReportStatus, ResearchState


def compare(state: ResearchState) -> dict:
    by_country = {report.country: report for report in state.get("reports", [])}
    ordered = [by_country[code] for code in state["countries"] if code in by_country]
    missing = [
        code
        for code in state["countries"]
        if code not in by_country or by_country[code].status is not ReportStatus.OK
    ]
    return {"comparison": Comparison(query=state["query"], reports=ordered, missing=missing)}
