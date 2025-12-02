from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/ui", response_class=HTMLResponse)
async def usage_dashboard():
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Proxy Usage Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        h1 {
            font-size: 28px;
            margin-bottom: 10px;
            color: #1a1a1a;
        }

        .subtitle {
            color: #666;
            font-size: 14px;
        }

        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .control-group {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: flex-end;
        }

        .form-field {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        label {
            font-size: 13px;
            font-weight: 600;
            color: #555;
        }

        input, select, button {
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }

        input:focus, select:focus {
            outline: none;
            border-color: #4a90e2;
        }

        button {
            background: #4a90e2;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.2s;
        }

        button:hover {
            background: #357abd;
        }

        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .card h2 {
            font-size: 18px;
            margin-bottom: 20px;
            color: #1a1a1a;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }

        .stat {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #f5f5f5;
        }

        .stat:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #666;
            font-size: 14px;
        }

        .stat-value {
            font-weight: 600;
            font-size: 16px;
            color: #1a1a1a;
        }

        .stat-value.highlight {
            color: #4a90e2;
        }

        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }

        th {
            background: #f8f9fa;
            font-weight: 600;
            font-size: 13px;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        td {
            font-size: 14px;
        }

        tr:hover {
            background: #fafafa;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }

        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .empty {
            text-align: center;
            padding: 40px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Claude Proxy Usage Dashboard</h1>
            <p class="subtitle">Bedrock fallback 사용량 모니터링</p>
        </header>

        <div id="main-section">



        <div id="loading" class="loading" style="display: none;">
            로딩 중...
        </div>

        <div id="error" class="error" style="display: none;"></div>

        <div id="content" style="display: none;">
            <div class="grid">
                <div class="card">
                    <h2>전체 요약</h2>
                    <div class="stat">
                        <span class="stat-label">Total Users</span>
                        <span class="stat-value highlight" id="total-users">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Requests</span>
                        <span class="stat-value highlight" id="total-requests">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Input Tokens</span>
                        <span class="stat-value" id="input-tokens">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Output Tokens</span>
                        <span class="stat-value" id="output-tokens">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total Tokens</span>
                        <span class="stat-value highlight" id="total-tokens">0</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">예상 비용 (Bedrock)</span>
                        <span class="stat-value highlight" id="estimated-cost">$0.00</span>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>사용자별 사용량</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>User ID</th>
                                <th>요청 수</th>
                                <th>Input Tokens</th>
                                <th>Output Tokens</th>
                                <th>Total Tokens</th>
                                <th>예상 비용</th>
                            </tr>
                        </thead>
                        <tbody id="user-stats-body">
                        </tbody>
                    </table>
                </div>
                <div id="empty" class="empty" style="display: none;">
                    사용 데이터가 없습니다
                </div>
            </div>
        </div>
    </div>

    <script>
        function formatNumber(num) {
            return num.toLocaleString();
        }

        function calculateCost(inputTokens, outputTokens) {
            // Bedrock Claude Haiku 4.5 pricing (us-east-1)
            // Input: $0.80 per 1M tokens
            // Output: $4.00 per 1M tokens
            const inputCost = (inputTokens / 1000000) * 0.80;
            const outputCost = (outputTokens / 1000000) * 4.00;
            return inputCost + outputCost;
        }

        function formatCost(cost) {
            return '$' + cost.toFixed(4);
        }

        async function loadUsage() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('content').style.display = 'none';

            try {
                // Query all data (no date filter)
                const response = await fetch(`/v1/usage?request_type=bedrock&days=90`);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                document.getElementById('total-users').textContent = formatNumber(data.summary.total_users);
                document.getElementById('total-requests').textContent = formatNumber(data.summary.total_requests);
                document.getElementById('input-tokens').textContent = formatNumber(data.summary.total_input_tokens);
                document.getElementById('output-tokens').textContent = formatNumber(data.summary.total_output_tokens);
                document.getElementById('total-tokens').textContent = formatNumber(data.summary.total_tokens);
                
                const totalCost = calculateCost(data.summary.total_input_tokens, data.summary.total_output_tokens);
                document.getElementById('estimated-cost').textContent = formatCost(totalCost);

                const userStatsBody = document.getElementById('user-stats-body');
                userStatsBody.innerHTML = '';

                const userStats = Object.entries(data.users || {}).sort((a, b) =>
                    (b[1].input_tokens + b[1].output_tokens) - (a[1].input_tokens + a[1].output_tokens)
                );

                if (userStats.length === 0) {
                    document.getElementById('empty').style.display = 'block';
                    userStatsBody.closest('.table-container').style.display = 'none';
                } else {
                    document.getElementById('empty').style.display = 'none';
                    userStatsBody.closest('.table-container').style.display = 'block';

                    userStats.forEach(([userId, stats]) => {
                        const userCost = calculateCost(stats.input_tokens, stats.output_tokens);
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td><strong>${userId}</strong></td>
                            <td>${formatNumber(stats.requests)}</td>
                            <td>${formatNumber(stats.input_tokens)}</td>
                            <td>${formatNumber(stats.output_tokens)}</td>
                            <td>${formatNumber(stats.input_tokens + stats.output_tokens)}</td>
                            <td>${formatCost(userCost)}</td>
                        `;
                        userStatsBody.appendChild(row);
                    });
                }

                document.getElementById('content').style.display = 'block';

            } catch (error) {
                document.getElementById('error').textContent = `오류: ${error.message}`;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        // 페이지 로드 시 자동 조회 (전체)
        window.addEventListener('DOMContentLoaded', () => {
            loadUsage();
        });
        
        // 5분마다 자동 새로고침
        setInterval(loadUsage, 5 * 60 * 1000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
