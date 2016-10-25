#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2016 University of Dundee & Open Microscopy Environment.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Decorators for use with the webgateway application.
"""

import omeroweb.decorators
import logging
from django.http import JsonResponse
from functools import update_wrapper


logger = logging.getLogger(__name__)


class login_required(omeroweb.decorators.login_required):
    """
    webgateway specific extension of the OMERO.web login_required() decorator.
    """

    def on_not_logged_in(self, request, url, error=None):
        """
        Used for json api methods
        """
        return JsonResponse({'message': 'Not logged in'},
                            status=403)


class json_response(object):
    """
    Class-based decorator for wrapping Django views methods.
    Returns JsonResponse based on dict returned by views methods.
    Also handles exceptions from views methods, returning
    JsonResponse with appropriate status values.
    """

    def __init__(self):
        """Initialises the decorator."""
        pass

    # To make django's method_decorator work, this is required until
    # python/django sort out how argumented decorator wrapping should work
    # https://github.com/openmicroscopy/openmicroscopy/pull/1820
    def __getattr__(self, name):
        if name == '__name__':
            return self.__class__.__name__
        else:
            return super(json_response, self).getattr(name)

    def __call__(ctx, f):
        """
        Tries to prepare a logged in connection, then calls function and
        returns the result.
        """
        def wrapped(request, *args, **kwargs):
            logger.debug('json_response')
            try:
                rv = f(request, *args, **kwargs)
                return JsonResponse(rv)
            except Exception, ex:
                # Default status is 500 'server error'
                # But we try to handle all 'expected' errors appropriately
                # TODO: handle omero.ConcurrencyException
                status = 500
                trace = traceback.format_exc()
                if isinstance(ex, NotFoundError):
                    status = ex.status
                if isinstance(ex, BadRequestError):
                    status = ex.status
                    trace = ex.stacktrace   # Might be None
                elif isinstance(ex, omero.SecurityViolation):
                    status = 403
                elif isinstance(ex, omero.ApiUsageException):
                    status = 400
                logger.debug(trace)
                rsp_json = {"message": str(ex)}
                if trace is not None:
                    rsp_json["stacktrace"] = trace
                # In this case, there's no Error and the response
                # is valid (status code is 201)
                if isinstance(ex, CreatedObject):
                    status = ex.status
                    rsp_json = ex.response
                return JsonResponse(rsp_json, status=status)
        return update_wrapper(wrapped, f)
