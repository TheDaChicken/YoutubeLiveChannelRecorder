import json
import re

from ..log import info, stopped, warning
from ..utils.web import download_website, download_json
from ..utils.parser import parse_html_attributes
from ..utils.other import try_get

LOGIN_URL = "https://accounts.google.com/ServiceLogin?service=youtube"
LOOKUP_URL = 'https://accounts.google.com/_/signin/sl/lookup'
CHALLENGE_URL = 'https://accounts.google.com/_/signin/sl/challenge'
_TFA_URL = 'https://accounts.google.com/_/signin/challenge?hl=en&TL={0}'


def encode_post_data(*args, **kargs):
    try:
        from urllib.parse import urlencode as url_encode
    except ImportError:
        url_encode = None
        stopped("Unsupported version of Python. You need Version 3 :<")
    return url_encode(*args, **kargs).encode('ascii')


def login(username, password):
    """
    Attempt to log in to YouTube.
    True is returned if successful.

    Taken from and been edited:
        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L84

    :type username: str
    :type password: str
    """

    info("Attempting to Login to Youtube.")

    login_website = download_website(LOGIN_URL)

    if login_website is None:
        return [False, "No Internet!"]

    f = open("login_webpage.txt", "w+")
    f.write(str(login_website.encode('utf-8')))

    login_form = _hidden_inputs(login_website)

    def req(url, f_req):
        data = login_form.copy()
        data.update({
            'pstMsg': 1,
            'checkConnection': 'youtube',
            'checkedDomains': 'youtube',
            'hl': 'en',
            'deviceinfo': '[null,null,null,[],null,"US",null,null,[],"GlifWebSignIn",null,[null,null,[]]]',
            'f.req': json.dumps(f_req),
            'flowName': 'GlifWebSignIn',
            'flowEntry': 'ServiceLogin',
        })

        return download_json(
            url,
            transform_source=lambda s: re.sub(r'^[^[]*', '', s),
            data=encode_post_data(data), headers={
                'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Google-Accounts-XSRF': 1
            })

    lookup_req = [
        username,
        None, [], None, 'US', None, None, 2, False, True,
        [
            None, None,
            [2, 1, None, 1,
             'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube.com%2Fsignin'
             '%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop%26feature%3Dsign_in_button&hl'
             '=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page=PasswordSeparationSignIn',
             None, [], 4],
            1, [None, None, []], None, None, None, True
        ],
        username,
    ]

    lookup_results = req(
        LOOKUP_URL, lookup_req)

    if lookup_results is None:
        return [False, "ccc"]

    user_hash = try_get(lookup_results, lambda x: x[0][2], str)
    if not user_hash:
        return [False, 'Unable to extract user hash']

    challenge_req = [
        user_hash,
        None, 1, None, [1, None, None, None, [password, None, True]],
        [
            None, None, [2, 1, None, 1,
                         'https://accounts.google.com/ServiceLogin?passive=true&continue=https%3A%2F%2Fwww.youtube'
                         '.com%2Fsignin%3Fnext%3D%252F%26action_handle_signin%3Dtrue%26hl%3Den%26app%3Ddesktop'
                         '%26feature%3Dsign_in_button&hl=en&service=youtube&uilel=3&requestPath=%2FServiceLogin&Page'
                         '=PasswordSeparationSignIn',
                         None, [], 4],
            1, [None, None, []], None, None, None, True
        ]]

    challenge_results = req(
        CHALLENGE_URL, challenge_req)

    if challenge_results is None:
        return [False, "bb"]

    if challenge_results is 400:
        return [False, "Challenge returned as a Bad Request 400"]

    login_res = try_get(challenge_results, lambda x: x[0][5], list)
    if login_res:
        login_msg = try_get(login_res, lambda x: x[5], str)
        message = 'Google replied: Invalid password.\n' \
                  'This isn\'t always the case, ' \
                  'please try again in the next 24 hours!' if login_msg == 'INCORRECT_ANSWER_ENTERED' else login_msg
        return [False, message]

    res = try_get(challenge_results, lambda x: x[0][-1], list)
    if not res:
        return [False, "Unable to extract result entry"]

    login_challenge = try_get(res, lambda x: x[0][0], list)
    if login_challenge:
        challenge_str = try_get(login_challenge, lambda x: x[2], str)
        if challenge_str == 'TWO_STEP_VERIFICATION':
            return [False, "TWO STEP VERIFICATION is not yet supported!"]
    else:
        check_cookie_url = try_get(res, lambda x: x[2], str)

    if not check_cookie_url:
        return [False, 'Unable to extract CheckCookie URL.']

    check_cookie_results = download_website(check_cookie_url)

    if check_cookie_results is None:
        return [False, "Internet offline."]

    if 'https://myaccount.google.com/' not in check_cookie_results:
        return [False, 'Not able to log in!']

    info("Login Successful!")
    return [True, "OK"]


def _hidden_inputs(html):
    """
    Taken from https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/common.py#L1304
    """
    html = re.sub(r'<!--(?:(?!<!--).)*-->', '', html)
    hidden_inputs = {}
    for input_ in re.findall(r'(?i)(<input[^>]+>)', html):
        attrs = parse_html_attributes(input_)
        if not input_:
            continue
        if attrs.get('type') not in ('hidden', 'submit'):
            continue
        name = attrs.get('name') or attrs.get('id')
        value = attrs.get('value')
        if name and value is not None:
            hidden_inputs[name] = value
    return hidden_inputs


def logout():
    """
    Useless right now but logs out of Youtube.

    """
    info("Attempting to Logout of Youtube.")

    download_website("https://youtube.com/logout")
