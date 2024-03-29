T2WML API History
===================================
Changes in version 0.6.6:
------------------------
Slight refactor, added docs, no other significant changes in functionality

Changes in version 0.6.5:
------------------------
* refactor node creation to be in its own module

Changes in version 0.6.4:
------------------------
* fix some backwards compatibility problems in 0.6.3
* fix bug when fixing overlapping bocks and one block is None
* fix bug that assigned all properties the same label

Changes in version 0.6.3:
------------------------
* improve algorithm for detecting 1D blocks
* fix bug where block suggestions returned overlapping blocks

Changes in version 0.6.2:
------------------------
* don't allow overlapping or identical annotations
* remove very old defunct wikifierservice
* performance improvements

Changes in version 0.6.1:
------------------------
* faster wikifier
* improved alignment algorithm

Changes in version 0.6.0:
------------------------
* treat multi-column date blocks as concatenated dates
* remove post-processing of pandas data for multi-factor speedup of loading large spreadsheets 
* get rid of spreadsheet cache handling in api
* changes tags to dictionary by id rather than array
* speed up suggest_block algorithm for datasets with more than 300 rows by sampling top and bottom
* change iterator in statement mapper to accept start and end index, add option for "count" as well
* cache index_dict instead of recalculating each time.
* update country_wikifier_cache:
    - add more countries
    - standardize (lowercase, replace punctuation) 
    - add causx only countries for suggesting blocks
* bug fixes:
    - annotation parsing: fix bug with range strings


Changes in version 0.5.6:
------------------------
* critical bug fix in cleaning id


Changes in version 0.5.4:
------------------------
* additional fixes to -$n behavior

Changes in version 0.5.3:
------------------------
* conditionally use -$n in blocks that are 50% or more blank spaces
* bug fix when adding entities

Changes in version 0.5.2:
------------------------
* strip start/end whitespace from auto-generated node labels
* when auto-creating nodes, check if changed from property to qnode or vice versa
* bug fix to exception raised when label resolves to empty string
* stop using -$n in auto-generated blocks
* when generating kgtk output, skip cells with problem (instead of erroring out)
* do not send custom properties to sparql query service
* return filepath when getting entities from kgtk file


Changes in version 0.5.1:
------------------------
* remove every scrap of a print statement

Changes in version 0.5.0:
------------------------
* complete overhaul of wikification, extremely not backwards compatible (those with scripts can use OldItemTable if they need)
* remove wikifier_files from project
* tweak: raise error if clean_id returns empty string
* improve suggestion heuristic to check multiple cells and average them
* fix bug where suggestion heuristic treated empty cells as dates

Changes in version 0.4.3:
------------------------
* some changes to suggestion format
* annotation can accept a node dictionary or a node id string
* changes to autonode creation

Changes in version 0.4.2:
------------------------
Small refactors including adding things to api.py

Changes in version 0.4.0:
------------------------
A variety of stability and performance fixes

Changes in version 0.3.6:
------------------------
* don't autosuggest P1114
* change format of suggestion

Changes in version 0.3.5:
------------------------
* cache custom nodes in memory

Changes in version 0.3.4:
------------------------
* strict_make_numeric added
* some additional entries in country wikifier
* in auto blocks, find longerst stretch and allow 10% total length be skips
* fix race condition for wikified labels

Changes in version 0.3.3:
------------------------
* much faster block suggestion code
* added some countries to country wikifier
* improved string_is_valid check
* delete links to nonexistent blocks in autosuggested links
* add field entity_file to project

Changes in version 0.3.2:
------------------------
* add links field to annotation
* fix some bugs with subject field in annotation

Changes in version 0.3.1:
------------------------
* normalize block edges
* use subject from annotation if provided
* fix bug in overlap checking

Changes in version 0.3.0:
------------------------
* add auto block detection for dates, countries, and quantities
* add support for partial statements
* canonical spreadsheet:
    - fix bug in canonical spreadsheet that wasn't fetching labels
    - add dataset id
* preliminary support for limiting number of statements fetched (wip)
* order of statements switched to row-major
* add method for loading a Sheet from an in-memory csv string
* add support for simple imperfect alignments


Changes in version 0.2.11:
------------------------
* if value resolves to empty string don't create statement
* fix bug in warn_for_empty_cells
* refine make_numeric to only replace in beginning and end and to do a better job stripping whitespace and commas

Changes in version 0.2.9:
------------------------
* smoother handling of irregular numbers in annotations:
    * default to using make_numeric for anything of type quantity when creating yaml
    * use make_numeric when checking suggestion for quantityness
* don't send "title" in yaml

Changes in version 0.2.8:
------------------------
* canonical spreadsheet returns labels not qnodes
* added a function to suggest possible annotation choices for annotation blocks
* bug fix: added preloaded_properties.tsv to manifest.in when building package

Changes in version 0.2.6:
------------------------
* bug fix to creation of additional kgtk edges

Changes in version 0.2.5:
------------------------
* support additional data file formats (primarily tsv, but anything pandas' parser can detect should work in the api)
* added another 520 preloaded properties to the default provider
* in annotations:
    - only create custom properties for custom-node-id properties
    - drop duplicates from auto-gen wikifier
    - add file/sheet to autogen wikifier
    - don't overwrite user changes to auto-gen properties/items
    - make sure to update property types if linked annotation block type changes
    - allow value to be a wikidata item
    - major bug fix: non-existent properties were marked as existing and not generated properly
    - changed default descriptions to be empty strings (instead of "a item", "property relation")
* datamart mapping:
    - sanitize leading/trailing whitespace and trailing colon of names
    - add flag to validate variables as quantity



Changes in version 0.2.4:
------------------------
* bug fixes in error reporting during annotation generation (caused by index errors)
* add support for specifying precedence (True=overwrites others, False=all others overwrite) when adding entity and wikifier files
* during auto-creation of entities/wikication in annotations, precedence is lowest, and don't create empty files
* if a field is filled with an empty string in annotation, treat it as empty when assigning blocks

Changes in version 0.2.2:
------------------------
* also generate entities and wikification for units
* add id, userlink, and link fields to annotations
* support specifying sheet name and data path in wikifier file
* fix bug when autogen dir doesn't exist in filesystem
* remove project.t2wml file compatibility for formats from version 0.0.16 and earlier (was deprecated from 0.0.17 onwards)

Changes in version 0.2.1:
------------------------
* add some additional validation to annotation

Changes in version 0.2.0:
------------------------
* overhaul of kgtk output to include custom edges for dataset, variable nodes, qualifier nodes, custom QNodes, and linking statement edges to dataset
* add support for tags in entity upload
* add all properties from wikidata to a kgtk file and change the default wikidataprovider for api script users to be the kgtkfileprovider 
* change the format of errors to be a flat array of dictionaries instead of a layered dictionary
* in annotations, selections -> selection (backwards comaptibility will select first in list + print warning) 
* all rectangle orientations are normalized to top left corner to bottom right
* bug fixes:
    - handle $n cases in the annotations
    - specify an escape char in to_csv

Changes in version 0.1.0:
------------------------
* remove imprecise alignment support in annotations until we have a better working version
* add preliminary support for no_wikification setting and saving to a csv file
* add functions for renaming and deleting files in a project
* add description and url fields to project


Changes in version 0.0.22:
------------------------
* HOTFIX: broken addition of wikifier files

Changes in version 0.0.21:
------------------------
* bug fix: not normalizing path when adding files
* various tweaks to annotation parsing:
    * rudimentary support for annotating with imprecise alignments
    * in annotationmapper, if there isn't a valid annotation (dependent variable + main subject)- don't try generating statements
    * add basic annotation validation (must be a list containing dict entries with a key "role")

Changes in version 0.0.20:
------------------------
* munkres package added to requirements
* some module reorganization and cleanup
* added annotation_parsing module and AnnotationMapping class
* fix pandas xlrd bug
* until proper multi-wikifier file management is added, always use most recently applied wikifier file.

Changes in version 0.0.19:
------------------------
* added cleaning function fill_empty
* region field of yaml no longer expectes/requires a list (list support now prints deprecation warning)
* added munkres to requirements

Changes in version 0.0.18:
------------------------
* added support for qval, qcol, and region in qualifier
* item in yaml and statements has been renamed to "subject". for now there is backwards compatibility for older style yamls.
* statements no longer returns individual "cell" for item cell of statement and value of qualifier. instead, "cells" is returned, a dictionary of every field in the result (statement/qualifier) that was derived from a cell. (it will not work with concat, which does not support returning cell)
* added some more T2WML exception types, for project in particular
* fixed a small bug with references

Changes in version 0.0.17:
------------------------
* add support for leave/replace/add ethiopian calendar to gregorian
* change order of precedence when parsing regions - `cells` now supersedes all else
* change to project file format- save selected yamls and sheets 

Changes in version 0.0.16:
------------------------
* in make_numeric, return an empty string if fail to parse to number, and don;t convert floats to ints
* hot fix to how sparql queries are passed
* added sheet to knowledge graph (optional, backwards compatible) and to_json functionality to sheet
* bug fixes:
   * cast to path before calling as_posix
   * because of issues with numpy 1.19.4, make sure to list numpy version in requirements and setup
* slight output tweaks:
   * return key for unexpected errors in statement as well
   * slightly more information when wikify_region fails
* get rid of outdated error handling that included error codes for web
* update to valid property types: case insensitively: "globecoordinate", "quantity", "time", "string", "monolingualtext", "externalid", "wikibaseitem", "wikibaseproperty", "url" (externalid replaces externalidentifier, which was wrong)

Changes in version 0.0.15:
------------------------
* backwards incompatible: completely remove remaining ttl/rdf support
* backwards incompatible: the setting cache_data_files is now a property and cannot be directly set (instead, it is true when cache_data_files_folder is provided)
* new feature: as documented in grammar.md, a lot of cleaning functions added
    * IMPORTANT: this includes an added requirement, text-unidecode
    * backwards incompatible: some functions were renamed or replaced:
        - `replace` is gone, there's `replace_regex` now
        - `clean` has been renamed to `ftfy`
        - `title`, `upper`, `lower` are gone, there's a function `change_case` instead
        - `strip` is gone, use `strip_whitespace` instead
* included in the added cleaning functionality is the ability to add a `cleaningMapping` section to the yaml file to apply cleaning functions to specific sections of the calculated sheet
* the default sparql endpoint is now the public wikidata endpoint
* default WikidataProvider is now a DictionaryProvider with preloaded properties (we may change how preloading works in future version)
* allow uploading entities with wikidata IDs if user specifies `allow_wikidata_ids=True` in add_entities_from_file

Changes in version 0.0.14:
------------------------
* add state to project file
* bug fix when adding absolute file paths to project
* change format of project file to include sheet names
* remove specific wikifier support
* removed the ProjectRunner class
* add cache_id and and handle_calendar properties to Project class
* pre-release: some of the cleaning functions (strip_whitespace, remove_numbers, truncate, normalize_whitespace, change_case)

Changes in version 0.0.13:
------------------------
* validate P/Q node definitions (must begin with P/Q, Pnum where num<10000 or Qnum where num<1 billion not allowed)
* when fetching property type, fetch description and label while you're at it
* stop saving directory to project file

Changes in version 0.0.12:
------------------------
* deprecation: rename add_nodes_from_file to add_entities_from_file
* backwards incompatible: rename .t2wmlproj to project.t2wml, so that it can be viewed on mac and linux
* change default project title from "Untitled" to folder name

Changes in version 0.0.11:
------------------------
* rename add_wikidata_file to more accurate add_entity_file

Changes in version 0.0.10:
------------------------
* All at least somewhat backwards incompatible:
    * Changed project class filename to .t2wmlproj
    * added sparql endpoint and warn for empty cells settings to project
    * change add_properties_from_file to add_nodes_from_file, some changes to wikidata_provider interface (documented in api.md)
    * change returned dict key (from adding properties to file) from "present" to "updated"
* Bug fix:
    * when set to something like $sheet, which doesn't return ReturnClass, parsing would fail on attribute error

Changes in version 0.0.8:
------------------------
* added the Project class
* change settings to be class-based instead of a dictionary
* when caching, use an underscored version of the full path to the original file to create the cache name
* add setting `warn_for_empty_cells`, default False
* change how date parsing is handled: if format is provided, must stricly match format, otherwise will fuzzy-guess
* change default behavior for regex to return first group

Changes in version 0.0.7:
-------------------------
* support utf-8 encoding for yaml files
* bug fixes:
  - bug fix for spacey import errors
  - fixed bug reading value definitions in wikifier where value is numeric
  - read pandas dataframes as strings (fixes bug: Object of type Timestamp is not JSON serializable)
  - do not re-apply same skips (fixes bug: Multiple skip_rows conditions that apply to the same row causes error)
  - do not generate qualifier edges for empty values
  - empty data cells were not being skipped
  - skip cells were being saved in columns
  - "node2;kgtk:data_type" for location changed from "coordinate" to "location_coordinate"
  - added globe field to kgtk output
* change settings to be class-based instead of a dictionary
* add setting `cache_data_files_folder`
* when caching, use an underscored version of the full path to the original file to create the cache name

Changes in version 0.0.6:
-------------------------
* complete overhaul of region definition, added support for 'columns'/'rows'/'cells'
* backwards incompatible: 
     * changed 'skip_column/row/cell' to 'skip_columns/rows/cells'
     * renamed BaseStatementMapper to StatementMapper
     * KnowledgeGraph.save_download renamed to KnowledgeGraph.save_file
* added case insensitivity to property typing (ie, url, Url, URL now all valid)
* stop printing template errors
* bug fixes:
  - critical bug: did not recognise 0 column/0 row when wikifying
  - x->y is now valid (previously only worked with spaces, x -> y)
  - error when not sending any date formats
  - item and cell falsiness now explicitly defined

Changes in version 0.0.5:
-------------------------

* add support for list of date formats
* etk is now optional
* class SpreadsheetFile has been refined
* added class Statement
* statements are returned if they are valid (no errors in value, property, and item)
* qualifiers are included if they are valid (no errors in value, property)
* yet more docs, examples, tests

Changes in version 0.0.4:
-------------------------

* A lot more classes:
    - Wikifier class fully working, supports multiple wikifier definitions
    - ItemTable completely revamped, totally different storage and lookup mechanism including preferential lookup
    - Revamp of cell mapping, now with base class BaseStatementMapper and implementation YamlMapper
    - WikifierService class 

Changes in version 0.0.3:
------------------------

* DataFile is now SpreadsheetFile
* bug fix:  bad access to sparql endpoint
* add support for adding label and description when uploading properties in tsv

Changes in version 0.0.2:
-------------------------

* when wikify_region fails on specific cells, return error listing those cells, and wikify the rest
* create temporary csv with tempfile rather than manually
* add support for $filename to t2wml syntax
* add support for Url as property type
* do not include project name in kgtk id
* add metadata (sheet and filename) to results
* continued cleaning of server-specific code from the API

Changes in version 0.0.1:
-------------------------

* separated from the server code into own package
