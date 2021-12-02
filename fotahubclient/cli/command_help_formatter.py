import argparse

def set_command_parser_titles(parser, positionals_title='Commands', optionals_title='Options'):
    parser._positionals.title = positionals_title
    parser._optionals.title = optionals_title

class CommandHelpFormatter(argparse.HelpFormatter):

    def _format_usage(self, usage, actions, groups, prefix):
        if not prefix:
            return super(CommandHelpFormatter, self)._format_usage(usage, actions, groups, 'Usage: ')
        else:
            return super(CommandHelpFormatter, self)._format_usage(usage, actions, groups, prefix)

    def _format_args(self, action, default_metavar):
        if action.choices is not None:
            return 'COMMAND ...'
        else:
            return super(CommandHelpFormatter, self)._format_args(action, default_metavar)

    def _format_action(self, action):
        if type(action) == argparse._SubParsersAction:
            # Inject new class variable for subcommand formatting
            subactions = action._get_subactions()
            invocations = [self._format_action_invocation(a) for a in subactions]
            self._subcommand_max_length = max(len(i) for i in invocations)

        if type(action) == argparse._SubParsersAction._ChoicesPseudoAction:
            # Format subcommand help line
            subcommand = self._format_action_invocation(action)
            width = self._subcommand_max_length
            help_text = ''
            if action.help:
                help_text = self._expand_help(action)
            return '  {:{width}} -  {}\n'.format(subcommand, help_text, width=width)

        elif type(action) == argparse._SubParsersAction:
            # Process subcommand help section
            msg = ''
            for subaction in action._get_subactions():
                msg += self._format_action(subaction)
            return msg
        else:
            return super(CommandHelpFormatter, self)._format_action(action)