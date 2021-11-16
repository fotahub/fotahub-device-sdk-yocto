import argparse

def set_option_parser_titles(parser, optionals_title='Options'):
    parser._optionals.title = optionals_title

class OptionHelpFormatter(argparse.HelpFormatter):

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            return super(OptionHelpFormatter, self)._format_usage(usage, actions, groups, 'Usage: ')
        else:
            return super(OptionHelpFormatter, self)._format_usage(usage, actions, groups, prefix)