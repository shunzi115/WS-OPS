# 分页时，获取要展示的页数范围,这里是固定显示多少页
def get_page_range(page_total,page_obj):
    page_now = page_obj.number
    if page_obj.paginator.num_pages > page_total:
        page_start = page_now - page_total // 2
        page_end = page_now + page_total // 2 + 1

        if page_start <= 0:
            page_start = 1
            page_end = page_start + page_total
        if page_end > page_obj.paginator.num_pages:
            page_end = page_obj.paginator.num_pages + 1
            page_start = page_end - page_total
    else:
        page_start = 1
        page_end = page_obj.paginator.num_pages + 1

    page_range = range(page_start, page_end)
    return page_range