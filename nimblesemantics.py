"""

TODO need to check if ID is used in multiple varDecs

Group members: OCdt Liethan Velasco and OCdt Aaron Brown

Version: TODO: completion date

TODO: read this description, implement to make it true.

The nimblesemantics module contains classes sufficient to perform a semantic analysis
of Nimble programs.

The analysis has two major tasks:

- to infer the types of all expressions in a Nimble program and to add appropriate type
annotations to the program's ANTLR-generated syntax tree by storing an entry in the `node_types`
dictionary for each expression node, where the key is the node and the value is a
`symboltable.PrimitiveType` or `symboltable.FunctionType`.

- to identify and flag all violations of the Nimble semantic specification
using the `errorlog.ErrorLog` and other classes in the `errorlog` module.

There are two phases to the analysis:

1. DefineScopesAndSymbols, and

2. InferTypesAndCheckSemantics.

In the first phase, `symboltable.Scope` objects are created for all scope-defining parse
tree nodes: the script, each function definition, and the main. These are stored in the
`self.scopes` dictionary. Also in this phase, all declared function types must be recorded
in the appropriate scope.

Parameter and variable types can be recorded in the appropriate scope in either the first
phase or the second phase.

In the second phase, type inference is performed and all other semantic constraints are
checked.

"""

from errorlog import ErrorLog, Category
from nimble import NimbleListener, NimbleParser
from symboltable import PrimitiveType, Scope


class DefineScopesAndSymbols(NimbleListener):

    def __init__(self, error_log: ErrorLog, global_scope: Scope, types: dict):
        self.error_log = error_log
        self.current_scope = global_scope
        self.type_of = types

    def enterMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.create_child_scope('$main', PrimitiveType.Void)

    def exitMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.enclosing_scope


class InferTypesAndCheckConstraints(NimbleListener):
    """
    The type of each expression parse tree node is calculated and stored in the
    `self.type_of` dictionary, where the key is the node object, and the value is
    an instance of `symboltable.PrimitiveType`.

    The types of declared variables are stored in `self.variables`, which is a dictionary
    mapping from variable names to `symboltable.PrimitiveType` instances.

    Any semantic errors detected, e.g., undefined variable names,
    type mismatches, etc., are logged in the `error_log`
    """

    def __init__(self, error_log: ErrorLog, global_scope: Scope, types: dict):
        self.error_log = error_log
        self.current_scope = global_scope
        self.type_of = types

    # --------------------------------------------------------
    # Program structure
    # --------------------------------------------------------

    def exitScript(self, ctx: NimbleParser.ScriptContext):
        pass

    def enterMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.child_scope_named('$main')

    def exitMain(self, ctx: NimbleParser.MainContext):
        self.current_scope = self.current_scope.enclosing_scope

    def exitBody(self, ctx: NimbleParser.BodyContext):
        pass

    def exitVarBlock(self, ctx: NimbleParser.VarBlockContext):
        pass

    def exitBlock(self, ctx: NimbleParser.BlockContext):
        # TODO I don't think anything actually needs to be done here as it will never have an error
        #  and doesn't need typed.
        pass

    # --------------------------------------------------------
    # Variable declarations
    # --------------------------------------------------------

    def exitVarDec(self, ctx: NimbleParser.VarDecContext):

        # TODO - handle duplicated names

        # Creating mini-lookup dictionary for verification
        type_dict = {'Int': PrimitiveType.Int, 'Bool': PrimitiveType.Bool, 'String': PrimitiveType.String}

        # Extracting variable type declared, its primitive type,
        # and the ID declared
        var_text = ctx.TYPE().getText();
        var_primtype = type_dict[var_text];
        this_ID = ctx.ID().getText();

        # First thing to check is if we're declaring a duplicated variable name. Set ERROR if so and stop function.
        if self.current_scope.resolve(this_ID) is not None:
            self.current_scope.define(this_ID, PrimitiveType.ERROR, False);
            self.error_log.add(ctx, Category.DUPLICATE_NAME, f"Previously declared variable already has name"
                                                             f"{this_ID}. No duplicates are allowed.");
            return;

        # If no duplicate name, and if there was an assignment,
        # check if does not violate type constraint
        if ctx.expr() is not None:

            # Extract value of expression put for assignment
            expr_type = self.type_of[ctx.expr()];

            # Check if they match. If not, then there was a constraint violation
            if expr_type != var_primtype:

                self.current_scope.define(this_ID, PrimitiveType.ERROR, False);
                self.type_of[ctx] = PrimitiveType.ERROR;
                self.error_log.add(ctx, Category.ASSIGN_TO_WRONG_TYPE,
                                   f"Can't assign {str(expr_type)} to variable of type {var_text}");
                return;


        # If all input conditions met, create the symbol with the inuptted typeset the variable type accordingly
        self.current_scope.define(this_ID, var_primtype, False);


    # --------------------------------------------------------
    # Statements
    # --------------------------------------------------------

    def exitAssignment(self, ctx: NimbleParser.AssignmentContext):

        # The variable ID must already be declared, and be of the same type as
        # expr. If conditions are met, the variable symbol named ID takes on type of expr.
        # Otherwise, gets type ERROR

        this_ID = ctx.ID().getText();
        expr_type = self.type_of[ctx.expr()];
        symbol = self.current_scope.resolve(this_ID);

        # Checking if variable under ID has been declared. If not, record the error
        if symbol is None:
            self.error_log.add(ctx, Category.UNDEFINED_NAME, f"Can't assign value to undefined variable {this_ID}");
            return;

        # Otherwise, check if expr_type does not match variable type. If not, record the error
        if symbol.type != expr_type:
            self.error_log.add(ctx, Category.ASSIGN_TO_WRONG_TYPE, f"Can't assign value of type {expr_type} to variable"
                                                                   f" {this_ID} of type {symbol.type}.");


    def exitWhile(self, ctx: NimbleParser.WhileContext):
        if self.type_of[ctx.expr()] != PrimitiveType.Bool:
            self.error_log.add(ctx, Category.CONDITION_NOT_BOOL, f"Type {self.type_of[ctx.expr()]} is not of type bool")


    def exitIf(self, ctx: NimbleParser.IfContext):
        pass

    def exitPrint(self, ctx: NimbleParser.PrintContext):

        # If expression to print is of type ERROR, record accordingly in error log.
        if self.type_of[ctx.expr()] == PrimitiveType.ERROR:
            self.error_log.add(ctx, Category.UNPRINTABLE_EXPRESSION, f"Can't print expression of type "
                                                                     f"{PrimitiveType.ERROR}.");


    # --------------------------------------------------------
    # Expressions
    # --------------------------------------------------------

    def exitIntLiteral(self, ctx: NimbleParser.IntLiteralContext):
        self.type_of[ctx] = PrimitiveType.Int


    def exitNeg(self, ctx: NimbleParser.NegContext):

        # Are conditions met for an integer negation?
        if ctx.op.text == '-' and self.type_of[ctx.expr()] == PrimitiveType.Int:
            self.type_of[ctx] = PrimitiveType.Int

        # Are conditions met for a boolean negation?
        elif ctx.op.text == '!' and self.type_of[ctx.expr()] == PrimitiveType.Bool:
            self.type_of[ctx] = PrimitiveType.Bool;

        # If none, then error had occurred.
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_NEGATION,
                               f"Can't apply {ctx.op.text} to {self.type_of[ctx].name}")


    def exitParens(self, ctx: NimbleParser.ParensContext):
        self.type_of[ctx] = self.type_of[ctx.expr()]
        if self.type_of[ctx.expr()] == PrimitiveType.ERROR:
            # TODO idk if this is the right way to handle an error but can't find a better way rn
            self.error_log.add(ctx, Category.INVALID_BINARY_OP, f"Error with expression")


    def exitMulDiv(self, ctx: NimbleParser.MulDivContext):
        left = self.type_of[ctx.expr(0)]
        right = self.type_of[ctx.expr(1)]
        if left == PrimitiveType.Int and right == PrimitiveType.Int:
            self.type_of[ctx] = PrimitiveType.Int
        else:
            self.type_of[ctx] = PrimitiveType.ERROR
            self.error_log.add(ctx, Category.INVALID_BINARY_OP,
                               f"Can't multiply or divide {self.type_of[ctx.expr(0)]} with {self.type_of[ctx.expr(1)]}")

    def exitAddSub(self, ctx: NimbleParser.AddSubContext):

        # If children types correct, set type of this token to Int
        if ((ctx.op.text == '+' or ctx.op.text == '-') and
            self.type_of[ctx.expr(0)] == PrimitiveType.Int and
                self.type_of[ctx.expr(1)] == PrimitiveType.Int):
            self.type_of[ctx] = PrimitiveType.Int;

        # Otherwise, set as error.
        else:
            self.type_of[ctx] = PrimitiveType.ERROR;
            self.error_log.add(ctx, Category.INVALID_BINARY_OP,
                               f"Can't apply {ctx.op.text} between non-integer type expression(s).");


    def exitCompare(self, ctx: NimbleParser.CompareContext):

        # Both left and right expressions must be integers. Results in a boolean type.
        # If these conditions are not met, error had occurred.
        left = self.type_of[ctx.expr(0)];
        right = self.type_of[ctx.expr(1)];
        if left == PrimitiveType.Int and right == PrimitiveType.Int:
            self.type_of[ctx] = PrimitiveType.Bool;
        else:
            self.type_of[ctx] = PrimitiveType.ERROR;
            self.error_log.add(ctx, Category.INVALID_BINARY_OP, f"Can't compare two non-integer type expressions.");


    def exitVariable(self, ctx: NimbleParser.VariableContext):

        # Simply check if ID is an existing var, or non-error type var.
        # If not, set type of ctx to be ERROR.
        this_ID = ctx.ID().getText();
        symbol_type = self.current_scope.resolve(this_ID);

        if symbol_type is None or symbol_type.type == PrimitiveType.ERROR:
            self.type_of[ctx] = PrimitiveType.ERROR;
            self.error_log.add(ctx, Category.UNDEFINED_NAME,
                               f"Variable {this_ID} is undefined.");
        else:
            self.type_of[ctx] = symbol_type;


    def exitStringLiteral(self, ctx: NimbleParser.StringLiteralContext):
        self.type_of[ctx] = PrimitiveType.String

    def exitBoolLiteral(self, ctx: NimbleParser.BoolLiteralContext):
        self.type_of[ctx] = PrimitiveType.Bool
