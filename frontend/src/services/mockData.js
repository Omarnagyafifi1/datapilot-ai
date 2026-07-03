export const mock = {
  generate: (question) => {
    const sql = `SELECT * FROM sales WHERE amount > 1000 -- generated for: ${question}`;
    return {
      sql,
      results: null,
      insights: [`Generated SQL for: "${question}"`],
    };
  },

  execute: (sql) => {
    // Return a small mock result set
    const results = [
      { id: 1, name: 'Alice', amount: 1200, region: 'North' },
      { id: 2, name: 'Bob', amount: 1500, region: 'West' },
      { id: 3, name: 'Carol', amount: 2000, region: 'East' },
    ];
    return {
      results,
      insights: [`Executed in mock mode for ${sql ? 'provided SQL' : 'mock SQL'}. Sample results returned.`],
    };
  }
};

export default mock;
