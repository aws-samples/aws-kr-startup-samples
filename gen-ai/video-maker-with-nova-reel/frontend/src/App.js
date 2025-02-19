import * as React from "react";
import Table from "@cloudscape-design/components/table";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import Button from "@cloudscape-design/components/button";
import TextFilter from "@cloudscape-design/components/text-filter";
import Header from "@cloudscape-design/components/header";
import Pagination from "@cloudscape-design/components/pagination";
import CollectionPreferences from "@cloudscape-design/components/collection-preferences";
import SideNavigation from "@cloudscape-design/components/side-navigation";

export default function App() {
  const [activeHref, setActiveHref] = React.useState("#/outputs");

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ width: '280px' }}>
        <SideNavigation
          activeHref={activeHref}
          header={{ href: "#/", text: "Video Generation Service" }}
          onFollow={event => {
            if (!event.detail.external) {
              event.preventDefault();
              setActiveHref(event.detail.href);
            }
          }}
          items={[
            { type: "link", text: "Outputs", href: "#/outputs" }
          ]}
        />
      </div>
      <div style={{ flex: 1, padding: '20px' }}>
        <InvocationsTable />
      </div>
    </div>
  );
}

function InvocationsTable() {
  // 페이지네이션 관련 상태값들
  const [currentPage, setCurrentPage] = React.useState(1);
  const [pagesCount, setPagesCount] = React.useState(1);
  // 각 페이지별 데이터를 저장 (key: 페이지 번호, value: 해당 페이지의 항목 배열)
  const [pageData, setPageData] = React.useState({});
  // 다음 페이지 호출 시 사용할 토큰. API 응답에 nextToken이 포함되어 있다고 가정.
  const [nextToken, setNextToken] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [selectedItems, setSelectedItems] = React.useState([]);
  
  const LIMIT = 20; // 한 페이지에 표시할 항목 수

  // 선택된 항목들 일괄 다운로드 핸들러
  const handleBulkDownload = async () => {
    try {
      // 선택된 모든 항목에 대해 순차적으로 다운로드 실행
      for (const item of selectedItems) {
        await handleDownload(item.invocation_id);
      }
    } catch (error) {
      console.error("일괄 다운로드 실패:", error);
    }
  };

  // 주어진 토큰과 페이지 번호를 이용해 데이터를 불러옴
  const fetchPage = async (token, page) => {
    setLoading(true);
    let url = `${process.env.REACT_APP_API_HOST}/apis/videos?limit=${LIMIT}`;
    if (token) {
      url += `&nextToken=${token}`;
    }
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
        mode: 'cors', // CORS 모드 명시적 설정
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      // api 응답은 { videos: [...], nextToken: "..." } 구조로 반환됩니다.
      // API가 video 항목을 { id, arn, prompt, status }로 반환한다고 가정하면,
      // 테이블의 컬럼에 맞게 키를 변환해줍니다.
      const videos = data.videos.map((video) => ({
        invocation_id: video.invocation_id,    // API의 id 값을 Invocation ID로 사용
        invocation_arn: video.invocation_arn,  // API의 arn 값을 Invocation ARN으로 사용
        prompt: video.prompt,
        status: video.status
      }));

      setPageData((prev) => ({ ...prev, [page]: videos }));
      setCurrentPage(page);
      if (data.nextToken) {
        setNextToken(data.nextToken);
        // 다음 페이지가 있을 경우 페이지 수를 현재 페이지 + 1로 확장
        setPagesCount(page + 1);
      } else {
        setNextToken(null);
        setPagesCount(page);
      }
    } catch (error) {
      console.error("데이터 불러오기 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트가 마운트될 때 첫 페이지 데이터를 불러옴
  React.useEffect(() => {
    fetchPage(null, 1);
  }, []);

  // Pagination onChange 핸들러
  const handlePageChange = (event) => {
    const newPage = event.detail.currentPageIndex;
    if (newPage === currentPage) return;
    // 이미 해당 페이지 데이터가 있다면 바로 전환
    if (pageData[newPage]) {
      setCurrentPage(newPage);
    } else {
      // 새로운 페이지라면, 기존의 nextToken을 사용해 다음 페이지를 불러옴.
      // (newPage는 현재 페이지보다 1 큰 경우에 해당)
      fetchPage(nextToken, newPage);
    }
  };

  // 다운로드 핸들러 추가
  const handleDownload = async (invocationId) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_HOST}/apis/videos/${invocationId}/download`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
        mode: 'cors',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `video-${invocationId}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error("다운로드 실패:", error);
    }
  };

  // 현재 페이지의 데이터 (데이터가 없으면 빈 배열)
  const items = pageData[currentPage] || [];

  return (
    <Table
      resizableColumns={true}
      renderAriaLive={({ firstIndex, lastIndex, totalItemsCount }) =>
        `전체 ${totalItemsCount}개의 항목 중 ${firstIndex}부터 ${lastIndex}까지 표시중`
      }
      columnDefinitions={[
        {
          id: "invocation_id",
          header: "Invocation ID",
          cell: (item) => item.invocation_id,
          sortingField: "invocation_id",
          isRowHeader: true,
        },
        {
          id: "invocation_arn",
          header: "Invocation ARN",
          cell: (item) => item.invocation_arn,
          sortingField: "invocation_arn",
        },
        {
          id: "prompt",
          header: "Prompt",
          cell: (item) => item.prompt,
          sortingField: "prompt",
        },
        {
          id: "status",
          header: "Status",
          cell: (item) => item.status,
          sortingField: "status",
        },
        {
          id: "actions",
          header: "Actions",
          cell: (item) => (
            <Button
              variant="inline-link"
              onClick={() => handleDownload(item.invocation_id)}
              ariaLabel={`${item.invocation_id} 다운로드`}
            >
              다운로드
            </Button>
          ),
          minWidth: 170
        }
      ]}
      items={items}
      loadingText="리소스를 불러오는 중"
      trackBy="invocation_id"
      empty={
        <Box margin={{ vertical: "xs" }} textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <b>리소스가 없습니다</b>
            <Button>리소스 생성</Button>
          </SpaceBetween>
        </Box>
      }
      filter={
        <TextFilter
          filteringPlaceholder="리소스 검색"
          filteringText=""
          countText="0 개의 항목"
        />
      }
      header={
        <Header>
          <SpaceBetween direction="vertical" size="xs">
            <Header
              counter={selectedItems.length ? `(${selectedItems.length}/${items.length})` : `(${items.length})`}
            >
              Outputs
            </Header>
            <SpaceBetween direction="horizontal" size="xs">
              <Button
                disabled={selectedItems.length === 0}
                onClick={handleBulkDownload}
              >
                {`선택한 항목 다운로드 (${selectedItems.length})`}
              </Button>
            </SpaceBetween>
          </SpaceBetween>
        </Header>
      }
      pagination={
        <Pagination
          currentPageIndex={currentPage}
          pagesCount={pagesCount}
          onChange={handlePageChange}
        />
      }
      preferences={
        <CollectionPreferences
          title="환경 설정"
          confirmLabel="확인"
          cancelLabel="취소"
          preferences={{
            pageSize: LIMIT,
            contentDisplay: [
              { id: "invocation_id", visible: true },
              { id: "invocation_arn", visible: true },
              { id: "prompt", visible: true },
              { id: "status", visible: true },
            ],
          }}
          pageSizePreference={{
            title: "페이지 크기",
            options: [
              { value: LIMIT, label: `${LIMIT} 개의 리소스` },
              { value: 20, label: "20 개의 리소스" },
            ],
          }}
          wrapLinesPreference={{}}
          stripedRowsPreference={{}}
          contentDensityPreference={{}}
          contentDisplayPreference={{
            options: [
              { id: "invocation_id", label: "Invocation ID", alwaysVisible: true },
              { id: "invocation_arn", label: "Invocation ARN" },
              { id: "prompt", label: "Prompt" },
              { id: "status", label: "Status" },
            ],
          }}
          stickyColumnsPreference={{
            firstColumns: {
              title: "첫 번째 열 고정",
              description: "가로 스크롤 시에도 첫 번째 열이 보이도록 설정합니다.",
              options: [
                { label: "없음", value: 0 },
                { label: "첫 번째 열", value: 1 },
              ],
            },
            lastColumnsPreference: {
              title: "마지막 열 고정",
              description: "가로 스크롤 시에도 마지막 열이 보이도록 설정합니다.",
              options: [
                { label: "없음", value: 0 },
                { label: "마지막 열", value: 1 },
              ],
            },
            lastColumns: {
              title: "마지막 열 고정",
              description: "가로 스크롤 시에도 마지막 열이 보이도록 설정합니다.",
              options: [
                { label: "없음", value: 0 },
                { label: "마지막 열", value: 1 },
              ],
            },
          }}
        />
      }
      selectedItems={selectedItems}
      selectionType="multi"
      onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
      ariaLabels={{
        selectionGroupLabel: "항목 선택",
        allItemsSelectionLabel: () => "모두 선택",
        itemSelectionLabel: ({ selectedItems }, item) => item.invocation_id
      }}
    />
  );
}