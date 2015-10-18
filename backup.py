#!/usr/bin/python

import gdata.sample_util
import gdata.sites.client
import os
from datetime import datetime
import re
import xml.parsers.expat
import atom.core

SOURCE_APP_NAME = 'backupApp-GoogleSitesAPIPythonLib'

class XmlParserSitesGData:
	def __init__(self, cache_file = None):
		self.cache_file = cache_file

	def GetStackNames(self):
		res = []
		for val in self.stack:
			res.append(val['name'])
		return res
	
	def IsCurrentStack(self, name, position):
		exp_name = position.pop()
		return cmp(self.GetStackNames(), position) == 0 and name == exp_name

	def start_element(self, name, attrs):
		#print 'Start element:', name, attrs, self.p.CurrentByteIndex

		if self.IsCurrentStack(name, ['feed', 'entry', 'content']):
			if self.content_start != 0:
				exit('content_start sanity check failed')
			self.content_start = self.p.CurrentByteIndex

		self.stack.append({
			'name': name,
			'parent': self.cur_el,
		})

		new_el = self.NewElement(name)
		new_el['attrs'] = attrs

		if self.xmltree is not None:
			self.cur_el['elements'].append(new_el)
		else:
			self.xmltree = new_el # root -- first initialization of the tree
			self.cur_el = self.xmltree

		self.cur_el = new_el

	def end_element(self, name):
		#print 'End element:', name, self.p.CurrentByteIndex
		prev_el = self.stack.pop()

		end_el = self.cur_el

		exp_name = prev_el['name']
		if exp_name != name:
			exit('stack mismatch: exp="%s", got="%s"' % (exp_name, name))

		self.cur_el = prev_el['parent']

		if self.IsCurrentStack(name, ['feed', 'entry', 'content']):
			if self.content_start == 0:
				exit('content_start sanity check failed')
			page_content = self.raw_xml[self.content_start:self.p.CurrentByteIndex]
			self.content_start = 0
			end_el['char_data'] = self.StripContentElement(page_content)
			# ignore what we parsed as XML -> we want the raw data
			end_el['elements'] = []

	def char_data(self, data):
		#print 'Character data:', repr(data)
		self.cur_el['char_data'].append(repr(data))

	def StripContentElement(self, s):
		m = re.search(r'^(\s*<\s*content(:?\s+[^>]+)?\s*>)', s, re.IGNORECASE)
		if m is None:
			exit('Unable to match the "content" element: %s' % (s))
		content_prefix = m.group(1)
		prefix_len = len(content_prefix)
		return s[prefix_len:]

	def NewElement(self, name):
		return {
			'name': name,
			'attrs': [],
			'char_data': [],
			'elements': [],
		}

	def HasCache(self):
		return self.cache_file is not None and os.path.exists(self.cache_file)

	def ReadRawXML(self, response):
		if self.HasCache():
			with open(self.cache_file, 'r') as fh:
				xmls = fh.read()
		else:
			xmls = response
			if self.cache_file is not None:
				with open(self.cache_file, 'w') as fh:
					fh.write(xmls)
		self.raw_xml = xmls

	def Parse(self, response):
		self.xmltree = None
		self.cur_el = self.xmltree
		self.stack = []

		self.content_start = 0

		self.ReadRawXML(response)

		self.p = xml.parsers.expat.ParserCreate()
		self.p.StartElementHandler = self.start_element
		self.p.EndElementHandler = self.end_element
		self.p.CharacterDataHandler = self.char_data
		self.p.Parse(self.raw_xml, 1)

		return self.xmltree
	
	@classmethod
	def FindAllElements(cls, data, name, attr_name = None, attr_value = None):
		"""
		Find all elements with the provided 'name'.
		Additionally filter by the provided attribute key/value, if provided.
		Return empty list, if none are found.
		"""

		ret = []
		for el in data:
			assert isinstance(el, dict)
			if el['name'] != name:
				continue # no match
			if attr_name is not None and attr_value is not None: # check 'attrs' too
				if attr_name not in el['attrs']:
					continue # no match
				if el['attrs'][attr_name] != attr_value:
					continue # no match
			# if we are here, we got an exact match
			ret.append(el)

		return ret

	@classmethod
	def FindOneElement(cls, data, name, attr_name = None, attr_value = None, none_is_ok = False):
		"""
		Find exactly one element with the provided 'name'.
		Additionally filter by the provided attribute key/value, if provided.
		If "none_is_ok" is True, then no exception is raised if none elements were found.
		Returns a list with one or none elements.
		"""

		ret = cls.FindAllElements(data, name, attr_name, attr_value)
		if len(ret) == 0:
			if not none_is_ok:
				exit(
					'%s::FindOneElement(%s): none elements found' % \
					(cls.__name__, name)
				)
			return None # XXX: return() here
		if len(ret) > 1:
			exit(
				'%s::FindOneElement(%s): too many elements found: count=%d' % \
				(cls.__name__, name, len(ret))
			)
		return ret[0]

class AtomCoreParseMonkeyPatch:
	def __init__(self, orig_function, debug_file):
		self.orig_function = orig_function
		self.xml_string = None
		self.debug_file = debug_file
	
	# XXX: The same signature as in "gdata-python-client.git/src/atom/core.py"
	def Parse(self, xml_string, target_class=None, version=1, encoding=None):
		assert self.xml_string is None

		self.xml_string = xml_string # cache it
		self.SaveDebugFile()

		return self.orig_function(xml_string, target_class, version, encoding)
	
	def GetTheCachedXML(self):
		return self.xml_string
	
	def SaveDebugFile(self):
		if self.debug_file is None:
			return
			
		with open(self.debug_file, 'w') as fh:
			fh.write(self.xml_string)
		

class SitesBackup:
	"""Backup your content using the Google Sites API functionality."""
	# some of the code references "samples/sites/sites_example.py"

	def __init__(self, debug = False):
		self.settings = gdata.sample_util.SettingsUtil()
		self.client = self.CreateSitesClient(debug)

	def CreateSitesClient(self, debug):
		"""Instantiate and authorize a Google Sites API client."""

		site_domain = self.PromptDomain()
		site_name = self.PromptSiteName()

		client = gdata.sites.client.SitesClient(
			source = SOURCE_APP_NAME, site = site_name, domain = site_domain
		)
		client.http_client.debug = debug

		try:
			self.AuthorizeClient(
				client = client,
				scopes = [
					'http://sites.google.com/feeds/',
					'https://sites.google.com/feeds/'
				]
			)
		except gdata.client.BadAuthentication:
			exit('Invalid user credentials given.')
		except gdata.client.Error:
			exit('Login Error')

		return client
	
	def AuthorizeClient(self, client, scopes):
		"""
		Use command line arguments, or prompt user for auth credentials.
		If a session file is provided, the auth token is cached there.

		This method is generic and should work for any "gdata client".
		"""

		session_file = self.settings.get_param(
			'session_file',
			'Session file to store the auth token [leave empty to skip]',
			reuse=True
		).strip()

		if not len(session_file):
			session_file = None

		client_id = self.settings.get_param(
			'client_id', 'Please enter your OAuth 2.0 Client ID '
			'which identifies your app', reuse=True
		)

		client_secret = self.settings.get_param(
			'client_secret', 'Please enter your OAuth 2.0 Client secret '
			'which you share with the OAuth provider', reuse=False
		)

		auth_kwargs = {
			'client_id': client_id,
			'client_secret': client_secret,
			'scope': " ".join(scopes), # http://stackoverflow.com/a/8451199/198219
			'user_agent': 'GdataPythonClientExample'
		}

		# the following code is adapted "Google API OAuth2 persistent token" by Zopieux
		# https://gist.github.com/Zopieux/22e18ecda720f0c67e01

		if session_file is not None and os.path.exists(session_file):
			with open(session_file, 'r') as fh:
				token = gdata.gauth.token_from_blob(fh.read())
				token = gdata.gauth.OAuth2Token(
					refresh_token=token.refresh_token, **auth_kwargs
				)
		else:
			token = gdata.gauth.OAuth2Token(**auth_kwargs)
			print '\nVisit the following URL in your browser '\
				'to authorize this app:\n\n%s\n' % \
					(str(token.generate_authorize_url()))
			code = raw_input('What is the verification code? ').strip()
			token.get_access_token(code)
			#client.auth_token = token
			if session_file is not None:
				with open(session_file, 'w') as fh:
					fh.write(gdata.gauth.token_to_blob(token))

		token.authorize(client)

	def PromptSiteName(self):
		"""Prompt the user to enter the site name."""

		site_name = ''
		trycount = 0
		while not len(site_name):
			if ++trycount > 1:
				print 'Please enter the name of your Google Site.'

			site_name = self.settings.get_param(
				'site',
				'Site name',
				reuse=True
			).strip()

		return site_name
	
	def PromptDomain(self):
		"""Prompt the user to enter the Google Apps domain, if any."""

		site_domain = self.settings.get_param(
			'domain',
			'If your Site is hosted on a Google Apps domain, '
			'enter it (e.g. example.com); otherwise leave empty',
			reuse=True
		).strip()

		if not len(site_domain):
			return 'site'
		else:
			return site_domain

	def DumpEntry(self, entry, out, raw_html):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		if entry.page_name:
			out['meta'].append(' page name:\t%s' % (entry.page_name.text))
		if entry.content:
			#out['content'] = str(entry.content.html)
			out['content'] = str(raw_html)
			if raw_html is None:
				exit('Raw HTML is none?')
		out['extension'] = 'html'

	def DumpListItem(self, entry, out):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		s = ''
		for col in entry.field:
			s += ' %s %s\t%s\n' % (col.index, col.name, col.text)
		out['content'] = s
		out['extension'] = 'txt'

	def DumpListPage(self, entry, out):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		s = ''
		for col in entry.data.column:
			s += ' %s %s\n' % (col.index, col.name)
		out['content'] = s
		out['extension'] = 'txt'

	def DumpFileCabinetPage(self, entry, out):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		out['meta'].append(' page name:\t%s' % (entry.page_name.text))
		out['content'] = str(entry.content.html)
		out['extension'] = 'xml'

	def DumpAttachment(self, entry, out):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		if entry.summary is not None:
			out['meta'].append(' description:\t%s' % (entry.summary.text))
		out['meta'].append(' content-type\t%s' % (entry.content.type))
		out['content'] = self.client._GetFileContent(entry.content.src)
		#out['extension'] = 'attachment'
		# no extension -> use the original URL name (and extension)

	def DumpWebAttachment(self, entry, out):
		out['meta'].append('%s [%s]' % (entry.title.text, entry.Kind()))
		if entry.summary.text is not None:
			out['meta'].append(' description:\t%s' % (entry.summary.text))
		out['meta'].append(' content src\t%s' % (entry.content.src))
		# no extension -> only a ".meta" file will be created

	def _StoreFile(self, dirname, filename_short, desc, content, kind):
		filename = '%s/%s' % (dirname, filename_short)

		print "%s (%s - %s)" % (filename, desc, kind)

		if not os.path.exists(dirname):
			os.makedirs(dirname)

		if os.path.exists(filename):
			exit('%s file already exists: %s' % (desc, filename))
		with open(filename, 'w') as fh:
			fh.write(content)

	def StoreBackupEntry(
			self, destdir, entity, href_dirname, href_filename, kind
	):
		bdir = '%s/%s' % (destdir, href_dirname)

		metafile = '%s.meta' % (href_filename)

		bfile = href_filename
		if 'extension' in entity:
			bfile = '%s.%s' % (bfile, entity['extension'])

		self._StoreFile(
			bdir, bfile, 'Entity',
			entity['content'],
			kind
		)
		self._StoreFile(
			'%s/__meta' % (bdir), metafile, 'Meta',
			"\n".join(entity['meta']).encode('utf-8'),
			kind
		)

	def _GetContentFeed_Google(self, next_link_href):
		# The standard implementation by Google.
		# Cache the "response" data and let the "gdata" library parse it.

		orig_atom_core_parse = atom.core.parse
		mp = AtomCoreParseMonkeyPatch(
			orig_atom_core_parse,
			None
		)
		atom.core.parse = mp.Parse

		feed = self.client.GetContentFeed(
			next_link_href
		)

		atom.core.parse = orig_atom_core_parse # restore original function

		cached_xml = mp.GetTheCachedXML()

		return (feed, cached_xml)

	def _GetContentFeed_Ours(self, cache_file = None, cached_xml = None):
		parser = XmlParserSitesGData(cache_file = cache_file)
		if not parser.HasCache():
			assert cached_xml is not None
			feed_raw = parser.Parse(cached_xml)
		else: # read from cache (useful only during development)
			assert cached_xml is None
			feed_raw = parser.Parse(None)

		return feed_raw

	def GetContentFeed(self, next_link_href = None):
		(feed, cached_xml) = self._GetContentFeed_Google(next_link_href)
		feed_raw = self._GetContentFeed_Ours(cached_xml = cached_xml)

		raw_html_content = {}
		for entry in XmlParserSitesGData.FindAllElements(feed_raw['elements'], name = 'entry'):
			pub_href = XmlParserSitesGData.FindOneElement(
			 	entry['elements'], name = 'link',
				attr_name = 'rel', attr_value = 'alternate'
			)
			pub_href = pub_href['attrs']['href']
			content = XmlParserSitesGData.FindOneElement(
				entry['elements'], name = 'content',
				none_is_ok = True
			)
			if content is not None:
				content = content['char_data']
			if pub_href in raw_html_content:
				exit('Encountering HREF "%s" for the second time' % (pub_href))
			raw_html_content[pub_href] = content

		return (feed, raw_html_content)

	def Run(self):
		destdir = self.settings.get_param(
			'backup_dir', 'Directory to store the backup', reuse=True
		).strip()
		if not len(destdir):
			destdir = '.'

		print "\nFetching & saving the content feed of '%s' ..." % (self.client.site)

		(feed, raw_html_content) = self.GetContentFeed()

		url_re = re.compile(r'^http(s)?:\/\/sites\.google\.com\/(.+)/([^\/]+)$')
		processed = set()
		while feed is not None:
			for entry in feed.entry:
				kind = entry.Kind()

				out = {}
				out['meta'] = []

				out['meta'].append(' id:\t%s' % (entry.GetId()))

				if entry.GetAlternateLink():
					pub_href = entry.GetAlternateLink().href

					if pub_href in processed:
						# avoid duplicates by GetContentFeed(next_link)
						continue
					processed.add(pub_href)

					out['meta'].append(
						' view in Sites:\t%s' % (pub_href)
					)
					m = url_re.match(pub_href)
					if not m:
						exit('Unable to parse URL: %s' % (pub_href))
					href_dirname = m.group(2)
					href_filename = m.group(3)
				else:
					exit('Unable to get the public Sites URL address')

				if kind == 'attachment':
					self.DumpAttachment(entry, out)
				#elif kind == 'webattachment':
				#	self.DumpWebAttachment(entry, out)
				#elif kind == 'filecabinet':
				#	self.DumpFileCabinetPage(entry, out)
				#elif kind == 'listitem':
				#	self.DumpListItem(entry, out)
				#elif kind == 'listpage':
				#	self.DumpListPage(entry, out)
				elif kind == 'webpage':
					self.DumpEntry(entry, out, raw_html_content[pub_href])
				else:
					exit('Unknown/untested kind: %s' % (kind))

				out['meta'].append(' revision:\t%s' % (entry.revision.text))
				out['meta'].append(' updated:\t%s' % (entry.updated.text))
				#updated_time = datetime.strptime(
				#	entry.updated.text, '%Y-%m-%dT%H:%M:%S.%fZ'
				#)

				parent_link = entry.FindParentLink()
				if parent_link:
					out['meta'].append(' parent link:\t%s' % (parent_link))

				if entry.feed_link:
					out['meta'].append(
						' feed of items:\t%s' % (entry.feed_link.href)
					)

				if entry.IsDeleted():
					out['meta'].append(' deleted:\t%s' % (entry.IsDeleted()))

				if entry.in_reply_to:
					out['meta'].append(
						' in reply to:\t%s' % (entry.in_reply_to.href)
					)

				self.StoreBackupEntry(
					destdir, out, href_dirname, href_filename,
					kind
				)

			# http://stackoverflow.com/a/27639711/198219
			next_link = feed.GetNextLink()

			print "Next page to fetch from the API? %s." % \
				('No' if next_link is None else 'Yes')

			if next_link is None:
				(feed, raw_html_content) = (None, None)
			else:
				(feed, raw_html_content) = self.GetContentFeed(next_link.href)

def main():
	backup = SitesBackup(debug=False)
	backup.Run()

if __name__ == '__main__':
	main()
