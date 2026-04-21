from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response


class LandingContentAPIView(APIView):
    def get(self, request):
        return Response({
            "hero": {
                "title": "Connect startups with investors",
                "subtitle": "Turn ideas into real businesses",
                "cta_text": "Join now",
                "hero_images": [
                    "/static/images/hero1.png",
                    "/static/images/hero2.png"
                ]
            },

            "for_whom": [
                {
                    "icon": "startup",
                    "title": "For Startups",
                    "desc": "Showcase your ideas and find investors"
                },
                {
                    "icon": "investor",
                    "title": "For Investors",
                    "desc": "Discover promising startups to invest in"
                },
                {
                    "icon": "partner",
                    "title": "For Partners",
                    "desc": "Collaborate and grow together"
                }
            ],

            "why_worth": [
                {
                    "title": "Fast Matching",
                    "desc": "Connect startups and investors quickly"
                },
                {
                    "title": "Secure Platform",
                    "desc": "Safe communication and data protection"
                },
                {
                    "title": "Scalable Network",
                    "desc": "Grow your business opportunities"
                }
            ],

            "footer_links": {
                "left": [
                    {"text": "About", "url": "/about"},
                    {"text": "How it works", "url": "/how-it-works"}
                ],
                "right": [
                    {"text": "Contact", "url": "/contact"},
                    {"text": "GitHub", "url": "https://github.com"}
                ]
            }
        })