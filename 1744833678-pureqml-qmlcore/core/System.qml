///object for storing general info about device and platform
Object {
	property string userAgent;	///< browser userAgent value
	property string language;	///< platform language
	property string browser;	///< browser name
	property string vendor;		///< current vendor name
	property string os;			///< operation system name
	property bool webkit;		///< webkit supported flag
	property bool support3dTransforms;	///< CSS transforms3d supported flag
	property bool supportTransforms;	///< CSS transforms supported flag
	property bool supportTransitions;	///< CSS transitions supported flag
	property bool portrait: parent.width < parent.height;	///< portrait oriented screen flag
	property bool landscape: !portrait;				///< landscape oriented screen flag
	property bool pageActive: true;					///< page active flag
	property int screenWidth;						///< device screen width value
	property int screenHeight;						///< device screen height value
	property int contextWidth: context.width;		///< @private
	property int contextHeight: context.height;						///< @private
	property int resolutionWidth;					///< app screen width from manifest
	property int resolutionHeight;					///< app screen height from manifest
	property enum device { Desktop, Tv, Mobile };	///< device type enumeration, values: Desktop, Tv or Mobile
	property enum layoutType { MobileS, MobileM, MobileL, Tablet, Laptop, LaptopL, Laptop4K };	///< layout type enumeration, values: MobileS, MobileM, MobileL, Tablet, Laptop, LaptopL and Laptop4K
	property bool virtualKeyboard: device === System.Tv || device === System.Mobile; ///< used to tweak components which use on-screen keyboard
	property bool tapHighlighted: os === "android" || os === "androidttk" || os === "hisense" || os === "ekt" || os === "sagem";
	property bool selectByMouse: !(tapHighlighted || os === "webos");

	/// @private
	onContextWidthChanged: { this._updateLayoutType() }
	/// @private
	onContextHeightChanged: { this._updateLayoutType() }

	/// @private
	_updateLayoutType: {
		if (!this.contextWidth || !this.contextHeight)
			return
		var min = this.contextWidth;// < this.contextHeight ? this.contextWidth : this.contextHeight

		if (min <= 320)
			this.layoutType = this.MobileS
		else if (min <= 375)
			this.layoutType = this.MobileM
		else if (min <= 425)
			this.layoutType = this.MobileL
		else if (min <= 768)
			this.layoutType = this.Tablet
		else if (this.contextWidth <= 1024)
			this.layoutType = this.Laptop
		else if (this.contextWidth <= 1440)
			this.layoutType = this.LaptopL
		else
			this.layoutType = this.Laptop4K
	}

	/// @private
	constructor: {
		this.vendor = $core.vendor
		this.device = $core.device
		this.os = $core.os

		this.browser = $core.browser
		this.userAgent = $core.userAgent
		this.language = $core.language

		var ctx = this._context
		ctx.language = this.language.replace('-', '_')
		this.webkit = this.userAgent.toLowerCase().indexOf('webkit') >= 0

		this.support3dTransforms = ctx.backend.capabilities.csstransforms3d || false
		this.supportTransforms = ctx.backend.capabilities.csstransforms || false
		this.supportTransitions = ctx.backend.capabilities.csstransitions || false

		this.resolutionWidth = $manifest$resolutionWidth
		this.resolutionHeight = $manifest$resolutionHeight
	}
}
