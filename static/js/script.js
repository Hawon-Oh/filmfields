


// search-bar 아무곳이나 클릭해도 input에 focus
document.getElementsByClassName("search-bar")[0].addEventListener("click", function() {
    document.getElementById("search-movie").focus();
});



// 검색어 입력 후 엔터 시 이동
document.getElementById('search-movie').addEventListener('keypress', function (event) {
    if (event.key === 'Enter') {
        const search_input = document.getElementById('search-movie').value.trim(); // 입력된 텍스트
        if (search_input) {
            // 현재 페이지에서 search.php로 이동하며 쿼리 파라미터 추가
            //flask이전코드 window.location.href = `search.php?q=${encodeURIComponent(search_input)}`;
            window.location.href = `/search?q=${encodeURIComponent(search_input)}`;
        }
    }
});



// 현재 URL에서 쿼리 파라미터를 가져오는 함수
const urlParams = new URLSearchParams(window.location.search);
const query = urlParams.get('q'); // 'q' 파라미터 값을 가져옴

// 쿼리 파라미터가 있을 경우 해당 값을 input 요소에 삽입
if (query) {
    document.getElementById('search-movie').value = query; // input 값 설정
}