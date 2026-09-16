#-*- coding:utf-8 -*-
import re
import os
import traceback
from aqt.utils import showInfo

__all__ = ['add_metaclass', 'wrap_css']


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


import tinycss2
from tinycss2.ast import QualifiedRule

def wrap_css_selectors(css_text: str, class_wrapper: str) -> str:
    wrapper_prefix = (
        class_wrapper if class_wrapper.startswith(".") else f".{class_wrapper}"
    )

    rules = tinycss2.parse_stylesheet(
        css_text, skip_whitespace=False, skip_comments=False
    )
    modified_rules = []

    # Parse raw prefix string into tokens once
    prefix_tokens = tinycss2.parse_component_value_list(f"{wrapper_prefix} ")

    for rule in rules:
        if isinstance(rule, QualifiedRule):
            new_prelude = []
            new_prelude.extend(prefix_tokens)

            # rule.prelude is already a list of tokens, iterate over it directly
            for token in rule.prelude:
                new_prelude.append(token)
                # If there's a comma (multiple selectors like `h1, p`), insert wrapper after the comma
                if token.type == "literal" and token.value == ",":
                    new_prelude.extend(prefix_tokens)

            rule.prelude = new_prelude

        modified_rules.append(rule)

    return tinycss2.serialize(modified_rules)


def wrap_css(orig_css, is_file=True, class_wrapper=None, get_canional_name=lambda x: x, new_css_file_suffix=u'wrapped'):
    if is_file:
        css_basename, ext = os.path.splitext(os.path.basename(orig_css))

        if not class_wrapper:
            class_wrapper = re.sub(r'^_+', '', css_basename)
        new_css_file = get_canional_name(f'{css_basename}_{new_css_file_suffix}.css')
        # if new css file exists, not process
        # if input original css file doesn't exist, return the new css filename and class wrapper
        # to make the subsequent process easy.
        if os.path.exists(new_css_file):
            return new_css_file, class_wrapper
        if not os.path.exists(orig_css):
            print(f"*** Error: {orig_css} does not exist, can't wrap!")
            return new_css_file, class_wrapper
        
        result = ''
        with open(orig_css, 'r', encoding='utf-8-sig') as f:
            try:
                result = wrap_css_selectors(f.read().strip(), class_wrapper)
            except:
                traceback.print_exc()
                showInfo('Error wrapping: ' + orig_css)

        if result:
            with open(new_css_file, 'w', encoding='utf-8') as f:
                f.write(result)
        return new_css_file, class_wrapper
    else:
        # class_wrapper must be valid.
        assert class_wrapper
        return wrap_css_selectors(orig_css, class_wrapper), class_wrapper
    
