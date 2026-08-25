import re

from django import template


register = template.Library()


@register.filter
def job_detail_id(job_id):
    if not job_id:
        return job_id

    return re.sub(r"_\[.*\]$", "", job_id)

