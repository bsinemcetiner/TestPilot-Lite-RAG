function Results() {
  return (
    <div>
      <h1 className="section-title">Results</h1>
      <div className="card">
        <p>
          After you generate test cases from the <strong>Generate Tests</strong> page, results will be displayed here.
        </p>
        <p>
          You'll be able to:
        </p>
        <ul>
          <li>View all generated test cases in a structured format</li>
          <li>See source document references for each test case</li>
          <li>Export results in multiple formats (JSON, Markdown, CSV, Gherkin)</li>
          <li>Review coverage and quality metrics</li>
        </ul>
      </div>
    </div>
  )
}

export default Results
