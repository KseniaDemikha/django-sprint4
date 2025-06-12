from django.core.paginator import Paginator

from .constants import NUMBER_OF_POSTS


def paginate_page(request, post_list, post_per_page=NUMBER_OF_POSTS):
    paginator = Paginator(post_list, post_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
