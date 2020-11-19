# The T2WML Grammar


* [Structure](#overallstructure)
    * [Overall structure](#overallstructure)
    * [The region](#regionstructure)
    * [The template](#templatestructure)
    * [cleaningMapping](#cleaningmapping)
    * [Conformance to Yaml Standards](#yamlstandards)
* [The T2WML Language](#language)
    * [Reserved keywords](#reserved)
    * [Value and Item](#valueitem)
    * [T2WML Functions](#functions)
        * [Booleans](#boolean)
            * [Operators](#operator)
            * [Functions](#boolfunc)
        * [String modifiers](#string)
        * [Other](#other)
    * [Miscellaneous](#misc)
* [Cleaning Functions](#cleaning)

## Structure
<span id="overallstructure"></span>

A valid T2WML file has a very specific structure it must conform to in order to work.

### The overall structure

````
statementMapping:
    region:
         - keys...
    template:
         - keys...
cleaningMapping:
    - region:
        - keys...
      functions:
        - func:
            args1:...
````


It must contain the key `statementMapping`, opening a dictionary.

The `statementMapping` must contain the keys `region` and `template`.

The `region` and the `template` must each be a list of dictionaries (although we currently only support one entry in the list)

It may optionally contain the key `cleaningMapping`, opening a list, discussed further in its section below.


### The region
<span id="regionstructure"></span>

The region is used to specify which cells of the data sheet are the data area.

The `region` can be written in a variety of formats. 

**Step one**: calculate the base rectangle.

1. The first option is to use the key `range` and specify a cell range, eg: `C4:E10`. 

2. The second option is to use the keys `left`, `right`, `top`, and `bottom`, to specify the left, right, top, and bottom edges of the area (inclusive). These arguments can be specified dynamically using the t2wml language. If left unspecified, left/right/top/bottom will default to the edges of the spreadsheet (ie the leftmost/rightmost columns and top/bottom rows)

The two options are mutually exclusive, if `range` is provided `top/bottom/left/right` will be ignored. If neither option is provided, the rectangle will default to the entire sheet.

**Step two**: Select/remove columns/rows/cells

There are six further, optional arguments the user can provide.

The arguments `columns`, `rows`, `cells` select specific columns, rows, and cells. These are not purely additive arguments-- another way of putting this is that selection arguments take priority over the base rectangle.

So, if someone provides a base rectangle of A1:E7 and then provides columns [A, B, E, G], the code will *select* columns A, B, E and ignore columns C and D, and the rows will be 1-7. If someone provides columns and rows, then the range argument will end up being ignored entirely. 

The arguments `skip_columns`, `skip_rows`, and `skip_cells` subtract from the selected rectangle (or selected rows+columns). 

`cells` takes precedence over any other arguments. For example, if in `cells` the user specifies A3, whose value is "dog", and in skip_cells the user says to skip all cells whose value is dog, A3 will *not* be skipped. 

**Dynamic definitions**:

All 6 arguments can be dynamically defined. **IMPORTANT**: When dynamically defined, the search for matches takes place exclusively within the base rectangle. So, going back to the example of A1:E7, if the columns argument was a dynamic definition that matched G, G would nonetheless not be included because the definition would not be searched for outside the rectangle. 

(This is especially important to be aware of for dynamically selecting cells, because a dynamic definition will NOT find cells outside of the rectangle. For cells outside of the rectangle you must specify them explicitly.)


#### Region example one
`````
region: 
     - left: A
       right: D
       top: 1
       bottom: 5
`````

#### Region example two
`````
region:
     - range: D3:F12
       skip_column:
            - code here...
            - more code...
       skip_cell:
            - more code...
`````

### The template
<span id="templatestructure"></span>

The template is used to build statements for each cell in the region.

It must have the keys `subject`, `property`, and `value`.

It can also optionally have the attribute keys `qualifier` and `reference`, as well as the optional keys `calendar`, `precision`, `time_zone`, `format`, `lang`, `longitude`, `latitude`, `unit`.

`qualifier`  must be a list of dictionaries. the required keys in their dictionaries are  `property` and `value`, and the same optional keys as above are allowed.

The values for the various keys can be defined in the T2WML language (`=value[$col, $row]` is a common occurence for the key `value`, for example).

#### Template example

`````
template: 
     value: =value[$col, $row]
     subject: Q1000
     property: P123
     qualifier:
           - property: P585
             value: 10
             format: "%Y"
           - property: P6001
             value: =item[A, $row]
     reference:
           - property: P246 # stated in
             value: Q11191 # The World Factbook

`````

### cleaningMapping
<span id="cleaningmapping"></span>

Providing a cleaningMapping section is optional, but if it is provided, it must conform to the following format:

It must contain a list.

Each entry of the list must be a dictionary, containing two keys, `region` and `functions`. The region is the same as the region in templateMapping and must follow the same format. `functions` is specific to cleaningMapping. It consists of a list of functions to be applied to the specified region (functions are describe in greater detail in the [cleaning Functions](#cleaning) section).

Some of the functions receive no arguments, some receive optional arguments, and some have required arguments. These are summarized below.

```yaml
cleaningMapping:
       - region: 
            range: D6:K20
         functions:
            - ftfy
            - strip_whitespace:
                char: null # default all whitespace, can also be " " or  "\t"
                where: start_and_end
            - replace_regex:
                to_replace: #required, no default
                replacement: #required, no default
            - remove_numbers:
                where: everywhere
            - remove_letters:
                where: everywhere
            - truncate:
                length: #required, no default
            - normalize_whitespace:
                tab: False
            - change_case:
                case: sentence #can also be "lower", "upper", and "title"
            - pad:
                length: #required, no default
                pad_text: #required, no default
                where: start # or "end". does not allow "everywhere" or "start_and_end"
            - make_numeric:
                decimal: "."
            - make_alphanumeric
            - make_ascii:
                translate: False
```

### Conformance to Yaml standards
<span id="yamlstandards"></span>

The T2WML grammar is based on yaml files that can contain custom T2WML statements. 

Therefore T2WML files must conform to [yaml 1.1 standards](https://yaml.org/spec/1.1/). (The yaml standards most likely to trip up a T2WML user are those regarding [escaping strings](http://blogs.perl.org/users/tinita/2018/03/strings-in-yaml---to-quote-or-not-to-quote.html), if you want a shorter document to read)

Note: It's not necessary to read this before writing T2WML yaml files. It's just something to be aware of if something goes wrong.

## The T2WML Language
<span id="language"></span>

By default, statements in the yaml document are parsed by the yaml parser (as ints, floats, strings, etc).

To indicate that a statement is an instance of T2WML code, the statement must be prefixed with an = sign.

`value: value[$col, $row]` will return the string "value[$col, $row]"
`value: =value[$col, $row]` will returned the evaluated value for the T2WML expression

<span id="reserved"></span>

The T2WML language contains some reserved variable names, indicated with a $ in front of the name

* `$top`, `$bottom`, `$left`, `$right` : The top, bottom, left, and right of the data range. Currently supported only when defining the region (not in template). Using for recursive definitions (left: $left+1) or circular definitions (right: $left, left: $right) is not allowed.
* `$end`: the last row of the sheet. Convenient for defining `bottom`.
* `$col`, `$row`: the current column and current row in the data region. Supported only in the template (not the region).
* `$n`: an iterator variable
* `$sheet`: the name of the current sheet

### Values and Items
<span id="valueitem"></span>

`value[col, row]` retrieves the cell contents for the cell/s indicated by col and row.

Col and row could be single constants:`value[A, 3]`. 

Either or both could be a range: `value[A:D, 4]`, `value[A:D, 3:5]`

And they can use the reserved values $col, $row, and $n: `value[A:$col, $row+$n]`

`item[col, row]` retrieves the wikidata item(s) based on the cell contents for the cell/s indicated by col, row

If the data cell contains the string "Burundi", for example, then item will retrieve the qnode "Q1000".

Be aware that when item[] values are being processed in boolean expressions, they are treated as the string representation of the qnode, ie, again "Q1000". Attempting to check whether item[col, row]=="Burundi" will fail, you need to check whether item[col, row]=="Q1000".

In order for item to work the user must have uploaded a wikifier file.

The valid col/row arguments are the same as for value. 

### Functions
<span id="functions"></span>

The T2WML language implements a variety of functions. 

These can be broadly split into boolean functions, string modifiers, and other. 

Functions can be nested. It is possible, for example, to write `contains((upper(value[A:B, 2:3])),”TA”)`, a case-insensitive way to check if the string “ta”, “tA”, etc is present in each cell in the range.

Not every nesting order makes sense.
`upper(contains(value[A:B, 2:3], “TA”))` would return a string, “FALSE” or “TRUE” (even worse, the string “FALSE” evaluates to True in boolean checks…) 


#### Boolean expressions and equations
<span id="boolean"></span>

A boolean expression- created with a function or operator- returns a True/False value.

A boolean equation is inidcated with the arrow (`->`) operator. It returns some value, based on when a boolean expression returns True. The left side argument is the boolean expression, and the right side argument is what is returned as soon as the expression is evaluated to True. (one therefore would normally have the boolean expression contain at least one of the iterables $row, $col, or $n)

`contains(value[A, $row], "human")` is a boolean expression. 

`contains(value[A, $row], "human") -> value[B, $row]` is a boolean equation.

`values[A, $row]=="human" -> value[B, $row]` is also a boolean equation

Note that `skip_col`, `skip_row`, and `skip_cell` in `region` expect to receive boolean *expressions*, not boolean equations. Where the return value of the function is True, the cell/row/column will be added to the list of cells/rows/columns to skip.

Empty cells will always evaluate to False.

##### Operators
<span id="operator"></span>

T2WML supports two boolean operators, `==` and `!=` for equal and not equal, respectively.

It is important to note that when applied to a *range*, these operators use "and" logic.

`value[A:D, $row] == "Burundi"` will only return true when all of the columns A through D in the row equal "Burundi". Similarly, `value[A:D, $row] != "Burundi"` will only return true if none of them equal "Burundi".

##### Boolean functions
<span id="boolfunc"></span>

There are currently four boolean functions.

It is important to note that when applied to a range, unlike operators, boolean functions use "or" logic. That means they will return True if the condition is True for any cell in the range.

1. `contains(arg1, arg2)`: whether the string value of arg1 contains arg2 (as a substring) anywhere.
2. `starts_with(arg1, arg2)`: same as contains but must start with arg2.
3. `ends_with(arg1, arg2)`: same as contains but must end with arg2.
4. `instance_of(input, qnode)`: checks whether the input has an "instance of" relationship with the qnode. both must be items or qnode strings. As described in the [Wikidata query tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial), the query uses “instance of” followed by any number of “subclass of”. ( wdt:P31/wdt:P279* )
  * `instance_of(“Q378619”, “Q146”)` would return True
  * `instance_of_qnode(item[A, 3], “Q146”)` would return True if the item for cell A3 was an instance of Q146, eg Q378619
  * `instance_of_qnode(value[B, 3], “Q146”)` would return True if the value for cell A3 was a string that happened to be a valid qnode string for a qnode that was an instance of Q146.
  * `instance_of_qnode(item[A, 3:6], “Q146”)` would return True if cells A3-A6 all were items that are instances of Q146

#### String modifiers
<span id="string"></span>
String modifier functions receive a value, value range, or string and perform various modifications on them.

If the string modifier receives a value range, it will perform the string modification on every value in the range.

It does not make sense to run string modifiers on items or item ranges, and attempting to do so will raise an error.

For simplicity, the examples all use a string for the input, but they would apply equally to a value for a cell whose contents are the string in the example, or a value range.

All of the [cleaning functions](#cleaning) can be used within the template yaml as string modifiers.

`split_index(input, split_char, i)`: Splits the input on the split_char, and returns the ith item from the split, where i is 1-indexed. For example, `split_index(“yes,no,maybe”, “,”, 2)` returns “no”

`substring(input, start (,end))`: Returns a substring of the input, from start to end, inclusive. (end is optional, if not provided the end will be the end of the string). Negatives indices are counted from the end of the string.

* `substring("platypus", 3)` returns “atypus”
* `substring("platypus", 3, 5)` returns "aty"
* `substring(“platypus”, 3, -2)` returns "atypu"

`extract_date(input, format_string)`: Attempts to extract a date from the input using etk, based on the format string.
For example, `extract_date(“2000”, “%Y”)` returns  2000-01-01T00:00:00

`regex(input, pattern (,i))`: Returns the value of the ith group in the regex pattern provided if a match is found. Returns None if no regex match is found. i is optional, if i is not provided the first group is returned (if no groups are specified, the entire match is returned). If you instead want to return all the groups, set i=0.

Example: 
* `regex("Isaac Newton, physicist",  "(\w+) (\w+)")` returns “Isaac Newton”
* `regex("Isaac Newton, physicist",  "(\w+) (\w+)", 1)` returns “Isaac”

The regex function uses Python's [re.search() function](https://docs.python.org/3/library/re.html) and hence Python's regex syntax. You can [test your regex](https://regex101.com/) to check that it is returning the results you expect.

**WARNING**: Because of the need to [conform to Yaml standards](#yamlstandards), a regex containing a colon *followed by whitespace* `: `, or whitespace followed by an octothorpe ` #`, requires special handling. The recommended solution is to not use actual whitespace, but rather the whitespace character `\s`, eg: `:\s`, `\s#`. You can also single-quote the entire line while double-quoting the regex string, eg: `value: '=regex(value[B, 2], "profile: (.*) \d{4}", 1)'`.

#### Other
<span id="other"></span>

Functions which do not behave like boolean functions or like string modifiers.

`get_item(input(, context))`

get_item receives an input which can be resolved to a string (for example, a value, the output of any string modifer, or just a string).

It optionally receives a context-- if no context is provided, the default context (`"__NO_CONTEXT__"`) is used.

It then looks up this string in the item table. If the string is not present in the item table it will return an error. Otherwise, it returns the item from the item table.

Obviously the preferred way to get an item from a string is to use the wikifier. `get_item` was created for situations where simply grabbing the string from a cell was not sufficient, for example, if it is necessary to use a regex on the cell to get the needed string.

example: `subject: '=get_item(regex(value[B, 2], "profile: (.*) \d{4}", 1))'`


`concat(*args)`

concat receives a variable number of arguments, **the last of which must be the join character**

For arguments that are ranges, rather than single values, concat will join everything in the range, in row-major order.


|     | A | B | C |
| --- | --- | --- | --- |
| 1   | Males  | Yes  | Bird  |
| 2   | Female  | No  | Fire  |
| 3   | Males  | Maybe  | Water  |

* `concat(value[B:C, 2:3], “implies”,  item[A, 1:2], “-”)`

Would return the string “No-Fire-Maybe-Water-implies-Q6581072-Q6581097”

Concat does not preserve row/column source information. This means that concat does not return information for highlighting in the spreadsheet, unlike string modifiers. (for example, if you define subject in your template to be concat(something), you won’t get blue highlighting) 


### Miscellaneous
<span id="misc"></span>

If for some reason you need a string value to start with "=" (and not have it be interepreted as T2WML code), you can escape it with a forward slash `/=`. If for some reason you need a string value to start with a forward slash followed by an equal sign, you can escape the initial forward slash with an additional forward slash `//=`. And so on. So `value: /=)` would return the string "=)"

This is only necessary at the beginning of a statement, forward slashes and equal signs in the middle of a string require no special treatment, eg: `value: The smiley /= is = to =/`

## Cleaning Functions
<span id="cleaning"></span>

Cleaning functions can be used to munge messy data.

They can be used as string modifiers in the template yaml, and act like any string modifier. But they can also be used in a separate cleaning section of the yaml, to create a cleaned copy of the data (the template section does not touch the underlying data, only the output result)


### Where

Several of the functions have a "where" argument. The valid values for where are "start", "end", "start_and_end", and "everywhere". Different functions have different defaults for where, indicated in the function signature.

### The functions

`strip_whitespace(input, char=None, where="start_and_end")`: Remove whitespace. By default will remove all whitespace, but if char argument (" " or "\t") is provided, will only remove that.

example: `strip_whitespace("\t  \w Hel l o?\tworld \t  ", where="everywhere")` becomes "Hello?world"

`normalize_whitespace(input, tab=False)`: replaces multiple consecutive whitespace characters with one space (also replaces other whitespace characters with one space). if Tab is True, replaces with one tab, instead.

example: `normalize_whitespace("Hello  you   hi\t this")` becomes "Hello you hi this"

`replace_regex(input, regex, replacement="", count=0)`: replace_regex uses underlying python [re.sub](https://docs.python.org/2/library/re.html#re.sub) functionality, `re.sub(regex, replacement, input, count)`. You can test that your regex performs as expected on websites like [regex101.com](https://regex101.com/) (make sure to select Python flavor and substitution). The default behavior for replacement is to replace with the empty string, ie remove. When count=0, it replaces everywhere. No `where` argument is provided, if you'd like to remove from the end, etc, you can arrange to do so with regex tokens like $ for end of string.

examples:

* `replace_regex("cats and dogs and cats", "cats", "turtles")` returns "turtles and dogs and turtles"
* `replace_regex(" 30 456 e", "[^\d.-]", "")` returns "30456"
* `replace_regex("123456790 ABC#%? .(朱惠英)", r'[^\x00-\x7f]', "")` returns "123456790 ABC#%? .()"
* `replace_regex("dan dan dan", "dan", "bob", 1)` returns "bob dan dan"


`remove_numbers(input, where=everywhere)`: remove the digits 0-9

examples: 

* `remove_numbers("123 hello1234hi 123")` returns " hellohi "
* `remove_numbers("123 hello1234hi 123", where=start)` returns " hello1234hi 123"

`remove_letters(input, where=everywhere)`: inverse of remove_numbers, leaves only digits and removes everything else (alpha version, may be redefined)

`change_case(input, case="sentence")`: Changes the case to one of "sentence", "lower", "upper", "title".

examples: 

case="tHe QUiCK brown fox"
       
* `change_case(case)` returns "The quick brown fox"
* `change_case(case, "lower")* `returns "the quick brown fox"
* `change_case(case, "upper")` returns "THE QUICK BROWN FOX"
* `change_case(case, "title")` returns "The Quick Brown Fox"

`truncate(input, length)`: if input is longer than length, return only first length number of characters from the string

example: `truncate("QWERTYUIOPASDFGHJKL", 10)` returns "QWERTYUIOP"

`pad(input, length, text, where=start)`: where can only be start or end. the main argument is a length in number of characters, which strings shorter than that length will be padded to. text is the string to be used in the padding, eg "\t". if the number of characters does not divide exactly then the cut-off depends on where. if where is start, the end of the pad string will be cut off, if where is end, the start of the pad string will be cut off. 

examples: 

* `pad("12345678", 11, "xo", where=start)` returns "xox12345678"
* `pad("12345678", 11, "xo", where=end)` returns "12345678oxo"

`ftfy(input)`:  Uses the [ftfy package](https://ftfy.readthedocs.io/en/latest/) to clean the input

example: `ftfy(schÃ¶n)` returns "schön"

`make_numeric(input, decimal=".")`: makes the value of a cell numeric by removing non-numeric characters (except for `-`, `e`, and `.`). The decimal argument allows numeric formats which use a different decimal characer than `.`. Support for LaTeX style numbers is not yet supported but may be added.

examples:

*  `make_numeric("1.977$")` returns "1.977"
* `make_numeric("1.554.677,88€", decimal=",")` returns "1554677.88"
* `make_numeric("1.577E20")` returns "1.577e+20" (python scientific notation)

`make_alphanumeric`: for now, removes all characters that are not true for isalnum(). May be redefined (eg to not remove spaces and punctuation...?)

example: `make_alphanumeric("Thanks 😊! (<hello>) חחחחⒶ -1.2e10")` would return "Thankshelloחחחח12e10"

`make_ascii`: either removes all non-ascii non-printable characters or, if translate=true,  uses [text-unidecode](https://pypi.org/project/text-unidecode/) to translate to closest equivalent

example: 

* `make_ascii("какой-то текст", translate=True)` returns "kakoi-to tekst", without translate the only ascii character there is the "-" so that's what would be returned
* `make_ascii("Thanks 😊! (<hello>) חחחחⒶ")` would return `"Thanks ! (<hello>) "`