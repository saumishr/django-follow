from django.contrib.auth.decorators import login_required
from django.db.models.loading import cache
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseServerError, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.conf import settings
from django.template.loader import render_to_string

from follow.utils import follow as _follow, unfollow as _unfollow, toggle as _toggle
from follow import utils
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from mezzanine.blog.models import BlogPost
from django.utils import simplejson
from follow.models import Follow

import json

def check(func):
    """ 
    Check the permissions, http method and login state.
    """
    def iCheck(request, *args, **kwargs):
        if not request.method == "POST":
            return HttpResponseBadRequest("Must be POST request.")
        follow = func(request, *args, **kwargs)
        if request.is_ajax():
            if isinstance(follow, Follow) :
                count = Follow.objects.get_follows(follow.target).count()
            else:
                count = Follow.objects.get_follows(follow).count()
            return HttpResponse(simplejson.dumps(dict(success=True,
                                                          count=count)))              
        try:
            if 'next' in request.GET:
                return HttpResponseRedirect(request.GET.get('next'))
            if 'next' in request.POST:
                return HttpResponseRedirect(request.POST.get('next'))
            return HttpResponseRedirect(follow.target.get_absolute_url())
        except (AttributeError, TypeError):
            if 'HTTP_REFERER' in request.META:
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            if follow:
                return HttpResponseServerError('"%s" object of type ``%s`` has no method ``get_absolute_url()``.' % (
                    unicode(follow.target), follow.target.__class__))
            return HttpResponseServerError('No follow object and `next` parameter found.')
    return iCheck

@login_required
@check
def follow(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _follow(request.user, obj)

@login_required
@check
def unfollow(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _unfollow(request.user, obj)


@login_required
@check
def toggle(request, app, model, id):
    model = cache.get_model(app, model)
    obj = model.objects.get(pk=id)
    return _toggle(request.user, obj)

def get_vendor_followers(request, content_type_id, object_id):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    obj = get_object_or_404(ctype.model_class(), pk=object_id)
    if request.is_ajax():
        return render_to_response("follow/friend_list_all.html", {
            "friends": utils.get_follower_users_for_vendor(obj),
        }, context_instance=RequestContext(request))
    else:
        return render_to_response("follow/render_friend_list_all.html", {
            "friends": utils.get_follower_users_for_vendor(obj),
        }, context_instance=RequestContext(request))

def get_vendor_followers_subset(request, content_type_id, object_id, sIndex, lIndex):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    obj = get_object_or_404(ctype.model_class(), pk=object_id)
    s = (int)(""+sIndex)
    l = (int)(""+lIndex)

    followers = utils.get_follower_users_subset_for_vendor(obj, s, l)

    if s == 0:
        data_href = reverse('get_vendor_followers_subset', kwargs={ 'content_type_id':content_type_id,
                                                            'object_id':object_id,
                                                            'sIndex':0,
                                                            'lIndex':settings.MIN_FOLLOWERS_CHUNK})

        return render_to_response("follow/friend_list_all.html", {
            "friends": followers,
            'is_incremental': False,
            'data_href':data_href,
            'data_chunk':settings.MIN_FOLLOWERS_CHUNK
        }, context_instance=RequestContext(request))

    

    if request.is_ajax():
	    context = RequestContext(request)

	    context.update({'friends': followers,
	                    'is_incremental': True})

	    template = 'follow/friend_list_all.html'
	    if followers:
	        ret_data = {
	            'html': render_to_string(template, context_instance=context).strip(),
	            'success': True
	        }
	    else:
	        ret_data = {
	            'success': False
	        }

	    return HttpResponse(json.dumps(ret_data), mimetype="application/json")

    else:
        return render_to_response("follow/render_friend_list_all.html", {
            "friends": followers,
        }, context_instance=RequestContext(request))       

def get_vendor_following(request, content_type_id, object_id):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    user = get_object_or_404(ctype.model_class(), pk=object_id)
    if request.is_ajax():
        return render_to_response("follow/vendor_following.html", {
            "vendors": utils.get_following_vendors_for_user(user),
        }, context_instance=RequestContext(request))
    else:
        return render_to_response("follow/render_vendor_following.html", {
            "vendors": utils.get_following_vendors_for_user(user),
        }, context_instance=RequestContext(request))       

def get_vendor_following_subset(request, content_type_id, object_id, sIndex, lIndex):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    user = get_object_or_404(ctype.model_class(), pk=object_id)
    s = (int)(""+sIndex)
    l = (int)(""+lIndex)
    isVertical = request.GET.get('v', '0')

    template = 'generic/vendor_list.html'
    if isVertical == '1':
        template = 'generic/vendor_list_v.html'

    vendors = utils.get_following_vendors_subset_for_user(user, s, l)

    if s == 0:
        data_href = reverse('get_vendor_following_subset', kwargs={ 'content_type_id':content_type_id,
                                                            'object_id':object_id,
                                                            'sIndex':0,
                                                            'lIndex':settings.MIN_FOLLOWERS_CHUNK})

        return render_to_response(template, {
            "vendors": vendors,
            'is_incremental': False,
            'data_href':data_href
        }, context_instance=RequestContext(request))

    

    if request.is_ajax():
        context = RequestContext(request)

        context.update({'vendors': vendors,
                        'is_incremental': True})


        if vendors:
            ret_data = {
                'html': render_to_string(template, context_instance=context).strip(),
                'success': True
            }
        else:
            ret_data = {
                'success': False
            }

        return HttpResponse(json.dumps(ret_data), mimetype="application/json")

    else:
        return render_to_response("follow/render_vendor_following.html", {
            "vendors": vendors
        }, context_instance=RequestContext(request))        